# cos-standards

Shared operating-model standards. A consuming repo calls these workflows from CI. A merge to `main` applies on the next run.

## Caller

```yaml
name: standards
on:
  pull_request:
  push:
    branches: [main]
jobs:
  lint:
    permissions:
      contents: read
    uses: alvin-t-mak/cos-standards/.github/workflows/lint.yml@main
  verify:
    permissions:
      contents: read
    uses: alvin-t-mak/cos-standards/.github/workflows/verify.yml@main
```

## Config

[`examples/cos.yaml`](examples/cos.yaml). What the checks cover, and what to delete after wiring: [`docs/checks.md`](docs/checks.md).

## Verification

Every adopting repo has a verify skill and a feature map, so an agent can prove the work the way a user would. The rule is [`docs/verification.md`](docs/verification.md). Copy [`examples/verify-app/`](examples/verify-app/) or [`examples/verify-vault/`](examples/verify-vault/). `cos-lint` fails when they are missing.

## Comments

`cos-check-comments` fails on a comment in Python, JS/TS, or shell. `cos-lint` runs it too. Pre-commit hook: [`examples/pre-commit-config.yaml`](examples/pre-commit-config.yaml).
