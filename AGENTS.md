# Agent notes

Load `docs/principles.md` and `docs/orchestrate.md` at the start of every task. Writing rules live in this package. Commit policy lives in `docs/orchestrate.md`.

A rule in this file and in `docs/*.md` is an HTML comment whose body is `rule:` plus the id. The shared ledger is `src/cos_standards/data/rules.yaml`. CI fails if a marked rule is missing from the ledger, or a ledger rule is not marked.

## Tasks

<!-- rule: task-dates -->
Tasks are checkboxes in the note the work belongs to. `📅 YYYY-MM-DD` is a hard external date. `⏳ YYYY-MM-DD` is a soft date. Never invent a `📅`. That call is a judgment. A malformed date fails CI.

<!-- rule: atomic-close -->
A project note has `status` of `active`, `waiting`, or `closed`. Closing is atomic: a ticked box, `status: closed`, `closed: YYYY-MM-DD`, and a one-line `CLOSED:` status, together.

## Checks

<!-- rule: different-agent-verifies -->
The agent that built a deliverable does not verify it. A different agent does, or the CI verify job does. Lint is an input. The verify job's rebuild receipt is the proof for a workbook.

<!-- rule: no-external-send -->
Never send Slack, email, or anything else, and never purchase anything, without Alvin's approval.

<!-- rule: no-vlookup -->
Build scripts use INDEX/MATCH. `VLOOKUP(`, `HLOOKUP(`, and `XLOOKUP(` fail CI.

<!-- rule: record-a-correction -->
The verifier, not the builder, appends `{id, note, count}` to the corrections file. At count 2, set `check` to the lint or CI check that blocks a repeat.

Slack drafts are files named `*.slack.md`. The shape is `docs/slack-style.md`.
