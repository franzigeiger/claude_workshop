# 🪩 Vibe Check — PaperClaw

## TL;DR
- **Score:** 64 / 100 — *Works for now. Drink some water before the agent gets ambitious.*
- **Biggest win:** Feedback loops — strict mypy + broad ruff + deptry + lefthook + one-command bring-up via mise.
- **Biggest miss:** No agentic review panel and no blast-radius friction; the human is still the first reviewer of every diff.
- **Do this now:** Add a `REVIEW.md` plus a `mise run review` task that fans out 3 specialist reviewers (security · python · maintainability) over `git diff main...HEAD`.
- **Earned bonuses:** 3 🎁🎁🎁

## 🌴 Stack detected
- **Language:** Python 3.14
- **Package manager:** uv
- **Toolchain notes:** mise · ruff (format + lint) · mypy strict · pytest · deptry · lefthook · gitleaks · httpx · pydantic

## Vibe Check Report Card

```
┌─────┬───────────────────────────────────────┬──────┬──────────────────────────────────────────────────────────────────────┐
│  #  │                 Item                  │ Vibe │                              Evidence                                │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│  1  │ AGENTS.md / CLAUDE.md                 │ 👍   │ AGENTS.md exists w/ stack + 5 non-obvious rules; CLAUDE.md symlinks  │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│  2  │ Strict type / compiler settings       │ 🚀   │ pyproject.toml: mypy strict + disallow_any_explicit + warn_unreach.  │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│  3  │ Strict linter / formatter             │ 🚀   │ ruff E/W/F/I/B/UP/SIM/RUF/TID/PL/PTH/ARG/ERA + ruff format in check  │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│  4  │ Schema validation at boundaries       │ ➖   │ pydantic is a declared dep; no API surface implemented yet           │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│  5  │ Logic separated from I/O              │ ➖   │ src/paperclaw is a scaffold (main + logging); nothing to evaluate    │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│  6  │ One-command bring-up                  │ 🚀   │ .mise.toml: setup / check / fmt; README mirrors them                 │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│  7  │ Pre-commit feedback loop              │ 👍   │ lefthook.yml wired; .git/hooks/ has only .sample — install via setup │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│  8  │ Dead-code guardrail                   │ 🚀   │ ruff F401/F841 enabled + deptry runs in mise check                   │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│  9  │ Logs reachable from terminal          │ 🚀   │ basicConfig(stream=sys.stdout); FileHandler banned in CLAUDE.md      │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│ 10  │ Docs stay in sync with code           │ 🩹   │ context.md mandates design.md upkeep; no hook enforces; doc drift   │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│ 11  │ Agent can self-test end-to-end        │ 🩹   │ uv run paperclaw exists & is in README, but only logs "scaffold OK" │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│ 12  │ Agentic review panel                  │ 💀   │ no REVIEW.md, no /review, no panel script                            │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│ 13  │ Friction proportional to blast radius │ 💀   │ no danger-zone hook, no CODEOWNERS, no named bypass                  │
├─────┼───────────────────────────────────────┼──────┼──────────────────────────────────────────────────────────────────────┤
│ 14  │ Tooling tuned for the agent           │ 👍   │ .gitleaksignore present + mise task names readable; no fix commands  │
└─────┴───────────────────────────────────────┴──────┴──────────────────────────────────────────────────────────────────────┘
```

### Item details

**1 · AGENTS.md / CLAUDE.md — 👍 Solid.** `AGENTS.md` (CLAUDE.md is a symlink to it) names the stack and lists five specific non-obvious rules: idempotent mutations, no swallowed errors, `pathlib.Path` everywhere, stdout-only logging, env-only `ANTHROPIC_API_KEY`. Good signal/noise. Missing: a "common commands" section so the agent doesn't have to grep `mise tasks` to find `mise run check`.
**Fix:** add a `## Commands` section listing `mise run setup | check | fmt` and `uv run paperclaw`.

**2 · Strict types — 🚀 Ship-Ready.** `pyproject.toml [tool.mypy]` is `strict = true` *and* layers on `warn_unreachable`, `warn_redundant_casts`, `warn_unused_ignores`, `disallow_any_explicit`. `mypy src tests` runs in `mise check`.

**3 · Strict linter / formatter — 🚀 Ship-Ready.** Ruff selects `E, W, F, I, B, UP, SIM, RUF, TID, PL, PTH, ARG, ERA` — well beyond defaults. `ruff format --check` and `ruff check` both gate `mise check`. Tests get sensible per-file ignores.

**4 · Schema validation at boundaries — ➖ N/A.** Pydantic is a declared dependency, but there's no API/CLI/IO surface yet for it to validate. Design.md §11 specifies a stable JSON envelope; once the CLI lands, that envelope is the thing to model with Pydantic.

**5 · Logic separated from I/O — ➖ N/A.** `src/paperclaw/__main__.py` is a 13-line scaffold. There is no business logic in the tree yet to evaluate.

**6 · One-command bring-up — 🚀 Ship-Ready.** `.mise.toml` defines `setup` (uv sync + `.env` copy + `lefthook install`), `check` (format · lint · mypy · deptry · pytest), and `fmt`. Same verbs work from anywhere in the repo. README documents both.

**7 · Pre-commit feedback loop — 👍 Solid.** `lefthook.yml` covers gitleaks, ruff format, ruff check `--fix`, mypy on pre-commit, and pytest on pre-push. Caveat: `.git/hooks/` currently contains only `.sample` files — hooks won't fire until someone runs `mise run setup`. That's standard, but worth a one-line nudge in AGENTS.md.

**8 · Dead-code guardrail — 🚀 Ship-Ready.** Ruff `F401` (unused imports) and `F841` (unused locals) are on; `deptry src` runs in `mise check` to catch orphan dependencies. Currently passes against the scaffold.

**9 · Logs reachable — 🚀 Ship-Ready.** `logging.basicConfig(stream=sys.stdout, ...)` and CLAUDE.md explicitly forbids `FileHandler`. An agent running the CLI sees everything.

**10 · Docs stay in sync — 🩹 Patchy.** `content/context.md` instructs the agent to keep `project.md` and `design.md` current, but nothing enforces it — no lefthook check, no CI rule, no AGENTS.md trigger. And `design.md` is already aspirational (describes a full Chroma + Ollama + tesseract pipeline) while the code is a 13-line `main`. Drift on day zero.
**Fix:** add a lefthook `pre-commit` rule that fails when `src/**/*.py` is staged without `content/**/*.md` if the diff isn't trivially additive.

**11 · Agent self-test end-to-end — 🩹 Patchy.** `uv run paperclaw` exists, is documented in README, and produces stdout — so the wiring is fine. But the binary only logs "paperclaw scaffold ready"; there is no ingest path or CLI subcommand the agent can drive to verify a change. Once subcommands land this becomes 🚀; today it's a stub.
**Fix:** stub the `paperclaw doctor` subcommand from design.md §11 first — it gives the agent a real return-something-meaningful entrypoint while the rest is built.

**12 · Agentic review panel — 💀 Broken.** No `REVIEW.md`, no `/review` slash command, no `mise run review` task, no instructions in AGENTS.md. Every diff routes through a single human.
**Fix:** add `REVIEW.md` (ignore-list of things not to flag), plus `mise run review` that fans out 3 specialist Claude reviewers (`security`, `python-idiomatic`, `maintainability`) over `git diff main...HEAD` and tiers by line count.

**13 · Friction proportional to blast radius — 💀 Broken.** No `CODEOWNERS`, no danger-zone glob in lefthook, no `PAPERCLAW_DANGER_OK=1` style bypass. Today the surface is small enough that this is theoretical — but the planned `~/library/` writer, the Chroma store reset, and `reclassify --stale` are all high-blast-radius operations.
**Fix:** add a lefthook `pre-push` rule that, when paths matching `src/paperclaw/store/**` or `categories.yaml` are changed, requires `PAPERCLAW_DANGER_OK=1` and prints a checklist (dry-run done · taxonomy_version bumped · reindex tested).

**14 · Tooling tuned for the agent — 👍 Solid.** `.gitleaksignore` exists and is set up for additive fingerprints. Mise task names (`setup`, `check`, `fmt`) are self-explanatory. Weakness: when a hook fails (mypy, ruff, deptry), the output is the tool's own — no wrapper printing "run `mise run fmt` to fix." For a workshop scaffold that's acceptable; for v1 it's a paper cut.
**Fix:** wrap the lefthook commands so a non-zero exit prints "to fix: `mise run fmt && git add -u`" or the analogous command.

## 🎁 Bonus finds
1. **`.mise.toml` pins the entire toolchain** (uv, lefthook, gitleaks) in one declarative file → `mise install` gives a new contributor or sandboxed agent a reproducible environment with no `brew install` dance.
2. **`CLAUDE.md → AGENTS.md` symlink** → both Claude Code and other agents read the same source of truth; no risk of two drifting files saying contradictory things.
3. **CLI design contract in `design.md` §11** — stable exit codes, JSON envelope on stdout, logs on stderr, no interactive prompts when stdin isn't a TTY → great agent-driveability spec; implementation will inherit it for free.

## 🎯 Vibe Score: 64 / 100

| Category | Items | Sub-score | Badge |
|---|---|---|---|
| 🧱 Foundations | 2, 3, 4 (N/A), 5 (N/A) | 20 / 20 | 🛡️ **Type-Safe Citizen** — earned |
| ⚡ Feedback Loops | 6, 7, 8, 9, 14 | 44 / 50 | 🚦 **Loop Closer** — earned |
| 🤖 Agent Enablement | 1, 10, 11, 12 | 13 / 40 | 🔍 Agent-Ready — *locked* |
| 🚨 Blast-Radius Safety | 13 | 0 / 10 | 🛟 Blast-Radius Aware — *locked* |

## 💊 Top 3 hangover preventions
1. **Stand up an agentic review panel.** Add `REVIEW.md` (what *not* to flag) and a `mise run review` task that runs ≥3 specialist reviewers over the local diff before the PR opens.
2. **Wire a docs-drift hook.** A lefthook `pre-commit` that warns when `src/**/*.py` is staged without a touch to `content/design.md` or `content/project.md`. Bonus: include a one-liner in AGENTS.md telling the agent how the check decides.
3. **Add blast-radius friction before you need it.** A glob-scoped pre-push check on `src/paperclaw/store/**` and `categories.yaml` that demands `PAPERCLAW_DANGER_OK=1` and prints the danger checklist. Cheap now, invaluable once Chroma + the renamer exist.

## 🪩 Verdict
*Works for now. Drink some water before the agent gets ambitious.* The foundations and feedback loops are genuinely strong — strict mypy, broad ruff, deptry, lefthook, one-command bring-up — and three real bonuses earn a **Vibe Pioneer** note. What holds the score back is everything that becomes load-bearing once the agent starts shipping code: no review panel, no docs-sync guard, no blast-radius friction, and a `paperclaw` CLI the agent can't yet drive end-to-end. Fix those four and you're at 85+ without touching the parts that are already good.

> 🌟 **Vibe Pioneer** — three genuine bonuses earned.
