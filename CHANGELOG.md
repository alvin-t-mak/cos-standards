# Changelog

## 0.2.0

Verification is required. The rule is [`docs/verification.md`](docs/verification.md). `cos-lint` and `cos-check-verify` fail an adopting repo that has no verify skill.

Adopting repos (personal-vault, veroa-vault, dinner-series, Caltrack, and later repos) add:

1. `.cursor/skills/verify-<name>/SKILL.md` with frontmatter `name`, `description`, and `verify`, and the sections Launch, Doctor, Drive, Evidence, Cleanup, and Helpers, in that order.
2. `features/README.md` plus one file per user-facing feature. Each feature file has the headings Sub-features, How to get to it (user POV), Driving it with <harness>, and Gotchas.
3. A `verify` command that is an executable script in the repo, `python` (or `python3`, `bash`, `sh`, `node`) plus a script, a Make target, or a package script. The forms are listed in `docs/verification.md`.
4. One end-to-end run before the skill counts: launch, doctor, drive one feature, capture evidence, clean up, and confirm the evidence is still there.

Copy [`examples/verify-app/`](examples/verify-app/) or [`examples/verify-vault/`](examples/verify-vault/) and replace every template slot. Vaults and other repos without a UI drive the CLI and the generated file (run the script, open the workbook or file, check the values) and check links and frontmatter.

The brief format in `docs/orchestrate.md` names that command and the evidence. The worker runs it and attaches the evidence. The verifier re-runs it. The check itself does not run the command.

The check also rejects a section that is only TBD, TODO, a dot, an HTML comment, or blank characters; any `<slot>` or `{{slot}}` in any case; a cleanup sentence that removes the evidence path; a verify path matched as a substring; a Make recipe or package script that names a missing file; and a description under 20 characters or silent on the surface.

Removal verbs match by stem, across a line break, including the proof and an `evidence/*` glob, unless that clause is negated. The noun cleanup is not a removal verb. clean, cleans, cleaned, and cleaning count when they act on the evidence path. A recipe or package script that is only `true`, `echo`, or `exit 0` fails, and every repo-relative path token in it must exist. A section with fewer than 3 words left after markup is stripped fails, as does a section that is only filler (not implemented, fill this later, coming soon, lorem ipsum, see the script, to be written). A slot is a bracketed placeholder word, not a URL, an HTML tag, or a YAML or JSON mapping. The package skip is this repo, which ships the check and the data files under `src/cos_standards/data/`.

Repos that already call `lint.yml` get this on the next run after 0.2.0 is on `main`. No workflow edit is required. The `cos.yaml` schema version stays 1.
