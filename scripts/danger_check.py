#!/usr/bin/env python3
"""Pre-push blast-radius guard for store/ and taxonomy changes."""

from __future__ import annotations

import os
import subprocess
import sys

_DANGER_PATTERNS = (
    "src/paperclaw/store/",
    "categories.yaml",
)

_CHECKLIST = """
╔══════════════════════════════════════════════════════════════════════╗
║  DANGER — store/ or categories.yaml changed                         ║
╚══════════════════════════════════════════════════════════════════════╝

Work through this checklist before pushing:

  □  Chroma schema: is the collection metadata schema still compatible
     with documents already in ~/.paperclaw/chroma?

  □  Filename stability: does dest_path() still produce the same path
     for every document already in ~/Documents/paperclaw-library?
     (A change here silently duplicates files on next ingest.)

  □  Taxonomy version: if kinds or topics changed in categories.yaml,
     was taxonomy_version bumped in that file?

  □  Reindex tested: have you run `paperclaw reindex --from-scratch`
     against a real library and confirmed the result is correct?

  □  Idempotency: does running `paperclaw ingest` twice still produce
     zero duplicates and zero unexpected changes?

Set PAPERCLAW_DANGER_OK=1 to bypass this check once you're done.
"""


def _push_files() -> list[str]:
    for cmd in (
        ["git", "diff", "--name-only", "origin/main..HEAD"],
        ["git", "diff", "--name-only", "main..HEAD"],
        ["git", "diff", "--name-only", "HEAD~1..HEAD"],
    ):
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip().splitlines()
    return []


def main() -> None:
    if os.environ.get("PAPERCLAW_DANGER_OK") == "1":
        sys.exit(0)

    files = _push_files()
    dangerous = [f for f in files if any(f.startswith(p) or f == p for p in _DANGER_PATTERNS)]

    if not dangerous:
        sys.exit(0)

    print(f"\nDangerous files in this push: {', '.join(dangerous)}", file=sys.stderr)
    print(_CHECKLIST, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
