# Agent notes

No comments in code. Agents must never add comments. Encode non-obvious invariants in names, types, or tests instead.

If a change touches a file matched by `standards/code-scope.yaml`, `docs/coding.md` applies in addition.

Lightfield automation work follows `docs/lightfield-automations.md`.

Shared rules for this repo live in `AGENTS.md` and `docs/principles.md`. `cos-check-comments` fails the tree when a comment is present. `cos-lint` runs that check.
