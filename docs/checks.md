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

<!-- rule: outward-names -->
Outward-facing folders and terms come from the repo config. A listed term fails on every matching line. A configured folder that is missing fails the check.

The rules ledger ties each marker (`rule:` plus the id) to a `check` id or an `uncheckable` reason. A local rule id that matches a shared id is rejected at load.

Corrections are `{id, note, count}`. At count 2, set `check` to the check that blocks a repeat.

`cos-verify` rebuilds each workbook in the models config, recalculates it with LibreOffice, and writes a receipt. It fails on value drift, Excel errors, a formula that contains the token CHECK, sheets not reached from a summary sheet, formulas with no cached value, and hardcoded summary numbers. A formula style matches a marker as a whole word, including at the start of the style name.

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
