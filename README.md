# cos-standards

Shared operating-model standards for Alvin Mak. [`veroa-vault`](https://github.com/alvin-t-mak/veroa-vault) and [`personal-vault`](https://github.com/alvin-t-mak/personal-vault) consume this repo. They do not copy it.

A change merged to `main` applies to both vaults on their next CI run.

## Consume

Add `.github/workflows/standards.yml`:

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
```

Add `cos.yaml` at the repo root, or the same file at `standards/local.yaml`. Point each path at a file or directory that exists in that repo. Format checks are per repo (`enabled`). Writing rules are not: local config can add a banned term or a ledger rule, and it cannot disable a shared one. There is no exemption key.

```yaml
version: 1
paths:
  - docs
extra_banned:
  - id: repo-specific-term
    category: phrase
    type: literal
    pattern: zz-local-term
    severity: error
    reason: Replace this with a term that belongs only in this repo.
deliverables:
  paths:
    - deliverables
  strict: true
slack:
  paths:
    - deliverables/slack
rules: standards/rules.yaml
corrections: standards/corrections.yaml
format:
  dates:
    enabled: true
    paths:
      - tasks
    require_weekday: false
  atomic_close:
    enabled: true
    paths:
      - tasks
  lookups:
    enabled: true
    paths:
      - models
    extra_functions: []
```

`standards/rules.yaml` and `standards/corrections.yaml` start empty. Shared ledger rules are added by this package. Put only repo-specific rules in the local file.

```yaml
version: 1
rules: []
```

```yaml
version: 1
corrections: []
```

Pass `config` when the file is not at either default path. Pass `ref` to pin a git ref. The default ref is `main`.

```yaml
jobs:
  lint:
    uses: alvin-t-mak/cos-standards/.github/workflows/lint.yml@main
    with:
      config: standards/local.yaml
      ref: main
```

Install the same tools locally with:

```bash
pip install "cos-standards @ git+https://github.com/alvin-t-mak/cos-standards"
```

`cos-lint` runs the writing lint, strict mode on deliverables, the Slack shape, the format checks the config turned on, and the rules and corrections ledgers.

## Delete local copies

Once a repo calls the workflow above, delete the vendored copies this package replaces:

- `standards/banned.yaml`
- `standards/banned.json`
- `standards/banned.md`
- `standards/lint_writing.py`
- `standards/test_lint_writing.py`
- `standards/.gen_banned_md.py`
- `standards/principles.md`
- `standards/orchestrate.md`
- `standards/tone.md`
- `standards/slack-style.md`
- `standards/lint_deliverables.py`
- `standards/lint_slack.py`
- `standards/lint_format.py`
- `standards/check_rules.py`
- `standards/check_corrections.py`
- `standards/check_generated.py`
- a workflow under `.github/workflows/` that vendors those checks, rather than calling this repo

Keep `cos.yaml` or `standards/local.yaml`, `standards/rules.yaml` (additions only), `standards/corrections.yaml`, and the caller workflow.

## Layout

`docs/` holds the prose: principles, orchestrate, tone, Slack style, and the generated banned list. `src/cos_standards/data/banned.yaml` is the writing-rule source. `cos-export-banned` rewrites `banned.json` and `docs/banned.md`.
