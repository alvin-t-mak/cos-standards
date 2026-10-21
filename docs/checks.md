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
Paths listed in `notion_paths` do not label a day light, buffer, or weekend. With no paths listed, this check reads nothing. It still runs.

Build scripts do not call `VLOOKUP(`, `HLOOKUP(`, `XLOOKUP(`, or `merge_cells`.

Outward-facing folders and terms come from the repo config. A listed term in one of those folders fails the check. The term list is the whole check.

The rules ledger ties each marker (`rule:` plus the id) to a `check` id or an `uncheckable` reason. A local rule id that matches a shared id is rejected.

Corrections are `{id, note, count}`. At count 2, set `check` to the check that blocks a repeat.

`cos-verify` rebuilds each workbook in the models config, recalculates it with LibreOffice, and writes a receipt. It fails on value drift, Excel errors, CHECK cells, sheets not reached from a summary sheet, formulas with no cached value, and hardcoded summary numbers.
