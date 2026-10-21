# cos-standards

Shared operating-model standards. A consuming repo installs this package and calls it from CI. It does not copy the checks.

A merge to `main` here applies on the next CI run of each consuming repo.

## Caller

Add `.github/workflows/standards.yml`. The job ids stay `lint` and `verify`, because branch rulesets key off those names.

```yaml
name: standards
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  lint:
    uses: alvin-t-mak/cos-standards/.github/workflows/lint.yml@main
  verify:
    uses: alvin-t-mak/cos-standards/.github/workflows/verify.yml@main
```

Optional inputs `config` and `ref` (default `main`):

```yaml
jobs:
  lint:
    uses: alvin-t-mak/cos-standards/.github/workflows/lint.yml@main
    with:
      config: standards/local.yaml
      ref: main
  verify:
    uses: alvin-t-mak/cos-standards/.github/workflows/verify.yml@main
    with:
      config: standards/local.yaml
      ref: main
```

## Config

`cos.yaml` at the repo root, or the same file at `standards/local.yaml`:

```yaml
version: 1
extra_banned:
  - id: repo-specific-term
    category: phrase
    type: literal
    pattern: zz-local-term
    severity: error
    reason: Replace this with a term that belongs only in this repo.
rules: standards/rules.yaml
corrections: standards/corrections.yaml
models: standards/models.yaml
notion_paths: []
vendor_notes:
  paths: []
  max_bullets: 4
  max_words: 25
slack:
  max_lines: 5
outward:
  folders: []
  terms: []
formula_style_prefixes: []
```

A consuming repo may add paths, add banned terms, add ledger rules, and set a stricter cap. Caps only move down: Slack lines at most 5, vendor bullets at most 4, vendor words at most 25. A check whose paths are absent reads nothing. It still runs.

`extra_banned` uses the same fields as the shared list, including an optional `allow` regex on that one new rule. `formula_style_prefixes` adds style-name fragments on top of Formula, Link, Total, Subtotal, and Major.

Models file, when `models` is set:

```yaml
models:
  - id: sample
    script: models/build_sample.py
    workbook: models/sample.xlsx
    summary_sheets:
      - Summary
```

A model entry has `id`, `script`, `workbook`, and `summary_sheets`. `summary_sheets` names at least one sheet. Any other key is rejected.

Outward file, or the `outward` block above:

```yaml
folders: []
terms: []
```

Local ledger additions and corrections:

```yaml
rules: []
```

```yaml
corrections: []
```

A correction is `{id, note, count}`. At count 2, set `check` to the check that blocks a repeat.

## Install

```bash
pip install "cos-standards @ git+https://github.com/alvin-t-mak/cos-standards"
```

`cos-lint` runs the writing lint in strict mode, Slack shape, task dates, atomic close, vendor-note caps, Notion day labels, `merge_cells`, lookup calls, outward terms, the rules ledger, and corrections. `cos-verify` rebuilds each configured workbook, recalculates it with LibreOffice, and writes `verify-receipt.json`. It fails on value drift, Excel errors, CHECK cells, sheets not reached from a summary sheet, formulas with no cached value, and hardcoded summary numbers. With no models and no `build_*.py` files, `cos-verify` exits 0.

## Delete after wiring

Delete the vendored copies this package replaces:

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

Replace a workflow that vendors those checks with the caller above. The job ids stay `lint` and `verify`.

Keep:

- `AGENTS.md`. Remove shared ids from the local rules file. Sections that belong only to that repo stay in `AGENTS.md`.
- `standards/rules.yaml`, with shared ids removed
- `standards/corrections.yaml`
- `standards/models.yaml`, each entry limited to `id`, `script`, `workbook`, and `summary_sheets`
- `standards/outward.yaml`, as `folders` and `terms`
- repo-local generators and the files they write, such as a map or a query refresh
