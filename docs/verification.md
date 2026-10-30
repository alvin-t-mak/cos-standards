# Verification

Every adopting repo has a scripted way for an agent to prove its work the way a user would. Launch the surface, drive a feature, and keep the evidence.

The practice is Lauren Tan's (@poteto), from [create-verification-skill](https://github.com/cursor/plugins/blob/main/pstack/skills/create-verification-skill/SKILL.md). The names of the sections and the proof rules are hers. This package turns them into a check every adopting repo has to pass.

<!-- rule: verify-skill -->
An adopting repo has `.cursor/skills/verify-<name>/SKILL.md`, a feature map under that folder, and a `verify` command that runs a script, Make target, or package script in the repo. `cos-lint` and `cos-check-verify` fail when any of that is missing, empty, or still holding a template slot. The standards package is the exception: the check skips a tree that contains `src/cos_standards/data/rules.yaml`, because that tree ships the check.

## Skill

Write the skill for the next agent. It will be read cold, mid-task, by an agent that has never seen the repo. Interview the repo first: what a person actually touches, how it starts, how an agent can drive it, what evidence can be captured, and whether two instances can run side by side. If they cannot, say so. Refusing to drive a shared instance is better than corrupting someone's session.

Frontmatter comes first, or the skill never registers:

```yaml
name: verify-<app>
description: Drive <app> the way a user does, on the <surface>. Use when proving a change to <app>.
verify: <command>
```

`name` matches the directory. `description` is at least 20 characters, names the surface (cli, shell, terminal, web, ui, api, browser, workbook, vault, markdown, desktop, or script), and says when to use the skill. `verify` is one command. These forms count:

- `scripts/verify` or `./scripts/verify`: a non-empty file in the repo, with a shebang, and the executable bit set
- `python scripts/verify.py`, and the same shape with `python3`, `bash`, `sh`, or `node`: the script exists and is non-empty
- `uv run` in front of either of those
- `make verify`: a `Makefile`, `makefile`, or `GNUmakefile` in the repo defines `verify:`. If the recipe runs a file in the repo, that file exists.
- `npm run verify`, `pnpm run verify`, `pnpm verify`, `yarn run verify`, or `yarn verify`: `package.json` has that script. If the script runs a file in the repo, that file exists.

No pipes, redirects, or a second command chained on. Flags on `make` are not part of the check.

The body has these sections, as `##` headings, in this order. Each one has real instructions under it. Extra headings are fine. The six are not. A body that is only TBD, TODO, a dot, an HTML comment, or blank characters (including zero-width characters) fails. The same rule applies to each feature heading.

- **Launch.** The command that starts the surface, and how you tell it is ready. Ready means a person can use it, including migrations and seed data. A health check can pass while init is still running. Include teardown. For a short-lived CLI there is no server: launch means install dependencies once, then start each drive in its own session.
- **Doctor.** One read-only check: is this instance worth driving? Process up, right build, port owned by this run, auth valid. An agent runs this first whenever something looks off.
- **Drive.** The harness recipe with real selectors or commands from this repo. Prefer stable handles (labels, data attributes, prompt strings, route paths) over coordinates and tab order.
- **Evidence.** What to capture, and the directory it goes to. Quote that directory in backticks. It lives under `evidence/`.
- **Cleanup.** Tear down only what this run started. Do not kill by process name. Quote the same `evidence/` path as Evidence. In that same sentence, say do not delete (or never delete) that path. A sentence that runs rm, delete, or remove on the evidence path fails, even if some other sentence says do not delete.
- **Helpers.** Any script the skill ships is executable, and the verify command path is written here as its own token. `not-scripts/verify` does not count as `scripts/verify`. A helper the reader has to reverse-engineer is not a helper.

A slot left in the skill fails the check. Any angle-bracket slot or `{{ }}` slot fails, in any case, including `<TODO>`, `<App>`, `< name >`, and `{{app}}`. The check reads `SKILL.md`, every `features/*.md` file, and any helper file under the skill directory.

## Feature map

`features/README.md` is the index. It links each feature file. One file per user-facing feature, in that same directory, starting with the main three to five (routes, commands, menus, or docs). Each file has these `##` headings:

- Sub-features
- How to get to it (user POV)
- Driving it with <harness>
- Gotchas

`<harness>` is the real tool: `shell`, `playwright`, `curl`, `openpyxl`. Each heading has text under it.

The map is the maintained source for proof. A drive that uses one convenient entry point is incomplete when the map lists others. If the seed data lacks a precondition a journey needs, the journey fails and the reason goes in that feature's Gotchas. Do not weaken the journey to make it pass.

## Evidence

A proof does all of these:

- Exercise the real user path. Internal setters and test-only endpoints do not count.
- Capture the action and the resulting state, including the final screen.
- Check side effects (files written, rows inserted, messages sent) along with what is visible.
- Mock only where production already isolates the external system. When the safe path is a dry-run or a test mode, check what it skips by watching files, network, and git refs. Some dry-runs still touch the network or open a browser.

Quote the evidence directory the same way in Evidence and in Cleanup, both in backticks, both under `evidence/`. A trailing slash does not matter. `evidence/<app>/log.txt` and `evidence/<app>` count as the same directory.

## Vaults and other repos without a UI

personal-vault, veroa-vault, and repos like them have no app to click. The surface is the CLI scripts and the files they generate, plus the markdown around them. Drive means:

- Run the script from the repo root, the way a person would.
- Open the workbook or other file it wrote and check the values. For a workbook, read the cells. Do not stop at "the script exited 0."
- Check links resolve and frontmatter matches the shape the repo requires.

Launch is not a server. It is "dependencies are present, then each drive runs in a clean output directory." Doctor checks the script, the inputs, and that the output directory is writable, and it does not write the artifact. Evidence is the command output plus the inspected file, under `evidence/<name>/`. Cleanup deletes scratch output and does not delete that directory.

dinner-series, Caltrack, and later apps use the same skill shape. Their Drive section is the UI, API, or CLI a person actually uses.

## Prove the skill once

Run the skill's own instructions end to end before calling it done: launch, doctor, drive one mapped feature, capture evidence, clean up. After cleanup, the evidence is still at the path the skill names. A cleanup that eats the proof fails this step. Fix what fails, and run cleanup after a failed attempt too, so a broken run does not leave processes and ports behind.

A skill that was never executed is a draft. The check confirms the files and the command. It does not launch the app. The brief is what makes an agent run the command, and the verifier runs it again.

If you proved the skill on a stand-in (a container instead of a fresh machine, a local stack instead of a remote one), list every setup step the stand-in did that the target will not. Those steps stay unverified until a run on the real target covers them.

When the app changes, update the map. Poteto's maintain-verification-skill skill is the loop for that.

## Briefs

`docs/orchestrate.md` is the brief format. VERIFY names this command and the evidence to attach. The worker runs the command and attaches the evidence. The verifier, a different agent or the CI verify job, re-runs the same command and checks the evidence. The worker does not grade the result.

## Templates

Copy one of these, then replace every slot with values from the repo:

- [`examples/verify-app/`](../examples/verify-app/) for a web UI, API, or CLI
- [`examples/verify-vault/`](../examples/verify-vault/) for markdown plus scripts that generate files

Put the copy at `.cursor/skills/verify-<app>/`. The pre-commit hook is in [`examples/pre-commit-config.yaml`](../examples/pre-commit-config.yaml).

## Migration

This requirement shipped in cos-standards 0.2.0. Repos that already call `lint.yml` pick it up on the next run after this release is on `main`. No workflow edit is required. Until the skill exists, `cos-lint` fails.

An adopting repo adds:

1. `.cursor/skills/verify-<name>/SKILL.md` with `name`, `description`, and `verify`, and the sections Launch, Doctor, Drive, Evidence, Cleanup, and Helpers.
2. `features/README.md` plus one file per user-facing feature, with the four headings above.
3. A `verify` command that the check can resolve, as listed under Skill.
4. One end-to-end run of that skill: launch, doctor, drive one feature, capture evidence, clean up, and confirm the evidence is still there.

The note for this release is [`CHANGELOG.md`](../CHANGELOG.md).
