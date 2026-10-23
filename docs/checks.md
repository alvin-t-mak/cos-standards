# Checks

A check is a small program. CI runs it. The builder does not grade its own work.

<!-- rule: banned-matches-generator -->
`banned.md` and `banned.json` are generated from `banned.yaml`. CI fails if either file differs from a fresh export.

The writing linter reads markdown, text, and string literals in Python. HTML is checked for dash rules only. It fails on em dashes, a double hyphen used as a dash, and the phrases in `banned.yaml`. En dashes are allowed. The linter skips fenced code, inline code, any line containing `lint: ignore`, and any file with `lint: ignore-file` in its first 5 lines. `cos-lint` is strict, so a warning fails the build.

Slack shape reads files named `*.slack.md`. A normal draft has at most 5 non-empty lines, uses `-` bullets, and has no semicolons. A decision request needs at least two numbered options, exactly one marked `(recommended)`, a line that starts with `Why`, and one line that states both the default and the deadline. The 5-line cap does not apply to a decision request.

Task lines: a 📅, ⏳, or ✅ marker must carry a real `YYYY-MM-DD`. Closed notes need a ticked box, `status: closed`, `closed: YYYY-MM-DD`, and a one-line `CLOSED:` status, together.

<!-- rule: vendor-notes -->
A file named `Vendor Notes.md` has at most 4 bullets under each `###` heading, at most 25 words in each bullet, and no date stamps. A lower cap is a stricter setting.

<!-- rule: notion-day-labels -->
Shared-doc paths do not label a day light, buffer, or weekend. The default scope is `Product/`, `Ops/Leadership Meetings/`, and `Website/Website Execution Checklist.md`. Paths in `notion_paths` add to that scope. An empty list leaves the defaults in place.

Build scripts do not call `VLOOKUP(`, `HLOOKUP(`, `XLOOKUP(`, or `merge_cells`.

No comments in code. Agents must never add comments. Encode non-obvious invariants in names, types, or tests instead. `cos-check-comments` fails on a Python `#` comment or a docstring, on a `//` or `/* */` comment in JavaScript or TypeScript, and on a shell `#` comment. `cos-lint` runs that check. A shebang on line 1, a Python encoding line on line 1 or 2, and a tool directive are allowed when the comment is only the directive. The directives are `# type: ignore`, `# noqa`, `# pragma: no cover`, `# pylint: disable`, `# pyright: ignore`, `# ruff: noqa`, `# mypy: ignore-errors`, `# fmt: off`, `# lint: ignore`, `# nosec`, `# isort: skip`, `eslint-disable`, `@ts-expect-error`, `prettier-ignore`, and `istanbul ignore`. A sentence after the directive fails. A docstring stays only when the same file passes `__doc__` or `name.__doc__` into a call, because a tool is reading it. The check skips `node_modules`, `.venv`, `venv`, `dist`, `build`, and `htmlcov`. A consuming repo runs `cos-check-comments`. The pre-commit hook is [`examples/pre-commit-config.yaml`](../examples/pre-commit-config.yaml).

<!-- rule: outward-names -->
Outward-facing folders and terms come from the repo config. A listed term fails on every matching line. A configured folder that is missing fails the check.

The rules ledger ties each marker (`rule:` plus the id) to a `check` id or an `uncheckable` reason. A local rule may set `check` to `job:` plus a job id, and that id must be a `jobs` key in `.github/workflows/*.yml`. A shared rule cannot use a job check. A local rule id that matches a shared id is rejected at load.

Corrections are `{id, note, count}`. At count 2, set `check` to the check that blocks a repeat.

`cos-verify` rebuilds each workbook in the models config, recalculates it with LibreOffice, and writes a receipt. It fails on value drift, Excel errors, a formula whose recalculated value is the text CHECK, sheets not reached from a summary sheet, formulas with no cached value, and hardcoded summary numbers. A formula style matches a marker as a whole word, including at the start of the style name.

Model entries are read at config load. `id`, `script`, `workbook`, and `summary_sheets` are the fields. Scanners read `dist/`, `build/`, `.venv/`, and `node_modules/` when those directories are present.

## Config

See [`examples/cos.yaml`](../examples/cos.yaml). Caps only move down. A local rules file cannot change a shared rule.

## Delete after wiring

- `standards/banned.yaml`
- `standards/banned.json`
- `standards/banned.md`
- `standards/lint_writing.py`
- `standards/lint_deliverables.py`
- `standards/lint_shape.py`
- `standards/lint_format.py`
- `standards/check_lookups.py`
- `standards/check_outward.py`
- `standards/check_rules.py`
- `standards/check_corrections.py`
- `standards/verify_models.py`
- `standards/.gen_banned_md.py`
- `standards/test_lint_writing.py`
- `standards/test_checks.py`
- `standards/tests/slack/good-decision.md`
- `standards/tests/slack/bad-decision.md`
- `standards/principles.md`
- `standards/orchestrate.md`
- `standards/tone.md`
- `standards/slack-style.md`
- `standards/README.md`

Replace a workflow that vendors those checks with [`examples/standards.yml`](../examples/standards.yml). Keep `AGENTS.md`, local rule additions, corrections, models (`id`, `script`, `workbook`, `summary_sheets`), outward `folders` and `terms`, and repo-local generators.
