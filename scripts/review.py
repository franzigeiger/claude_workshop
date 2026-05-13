#!/usr/bin/env python3
"""Agentic review panel — runs three specialist reviewers over the current branch diff."""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

_MODEL = "claude-opus-4-7"
_MAX_TOKENS = 1024

_REVIEWERS: list[tuple[str, str]] = [
    (
        "Security",
        "You are a security reviewer. Check for: hardcoded secrets or API keys, path traversal, "
        "command injection, insecure deserialization, "
        "unvalidated inputs crossing a trust boundary. "
        "Be concise — one bullet per finding. If nothing is wrong, say 'No issues found.' "
        "Ignore anything listed in REVIEW.md as intentional.",
    ),
    (
        "Correctness",
        "You are a correctness reviewer. Check for: logic bugs, unhandled exceptions, "
        "incorrect None handling, off-by-one errors, wrong assumptions about types, "
        "missing idempotency guards. Be concise — one bullet per finding. "
        "If nothing is wrong, say 'No issues found.' "
        "Ignore anything listed in REVIEW.md as intentional.",
    ),
    (
        "Architecture",
        "You are an architecture reviewer for PaperClaw, a Python 3.14 CLI. "
        "Check for: violations of the non-obvious rules in CLAUDE.md (idempotency, no silent "
        "swallows, pathlib only, stdout-only logging, no hardcoded API keys), unwanted coupling "
        "between ingest/store/agent layers, new behaviour without tests, functions > 200 LOC, "
        "modules > 1000 LOC. Be concise — one bullet per finding. "
        "If nothing is wrong, say 'No issues found.' "
        "Ignore anything listed in REVIEW.md as intentional.",
    ),
]


def _get_diff() -> str:
    for cmd in (
        ["git", "diff", "origin/main...HEAD"],
        ["git", "diff", "main...HEAD"],
        ["git", "diff", "HEAD"],
    ):
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
    return ""


def _read_review_md() -> str:
    path = Path(__file__).parent.parent / "REVIEW.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _run_reviewer(name: str, system: str, diff: str, review_md: str) -> tuple[str, str]:
    full_system = (
        f"{system}\n\n---\nREVIEW.md (do not flag these):\n{review_md}" if review_md else system
    )
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=full_system,
        messages=[{"role": "user", "content": f"Review this diff:\n\n```diff\n{diff}\n```"}],
    )
    block = response.content[0]
    text = block.text if isinstance(block, anthropic.types.TextBlock) else "(unexpected response)"
    return name, text


def main() -> None:
    diff = _get_diff()
    if not diff:
        print("No diff found — nothing to review.")
        sys.exit(0)

    review_md = _read_review_md()
    line_count = len(diff.splitlines())
    print(f"Reviewing {line_count} diff lines with {len(_REVIEWERS)} specialists...\n")

    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(_REVIEWERS)) as pool:
        futures = {
            pool.submit(_run_reviewer, name, system, diff, review_md): name
            for name, system in _REVIEWERS
        }
        for future in as_completed(futures):
            name, text = future.result()
            results[name] = text
            print(f"  ✓ {name}")

    print()
    for name, _ in _REVIEWERS:
        print(f"## {name} Review\n")
        print(results[name])
        print()


if __name__ == "__main__":
    main()
