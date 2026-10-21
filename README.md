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
