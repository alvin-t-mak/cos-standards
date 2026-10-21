# Orchestrate

How an agent runs a piece of work for Alvin. Adapted from lauren (@poteto): the brief is the product, standing orders travel with every spawn, and a completion still has to pass the checks.

The repo is the memory. Lint and CI replace human review. The builder never grades its own work. One source of truth per rule. When in doubt, delete.

## Standing orders

Paste this block into every brief and every resume.

1. The repo is the memory. If it is not written down here, it did not happen.
2. Lint and CI replace review. Do not ask Alvin to catch what a check can catch.
3. The builder never grades its own work. A different run of the checks does.
4. One source of truth per rule. Add a check. Do not add a second copy of the prose.
5. When in doubt, delete.
6. Nothing is sent, paid, or purchased without Alvin's approval.
7. Commit on a branch and open a PR. CI gates the merge. Do not commit to the default branch.
8. A local config may add rules. It may not disable a shared rule.

## Brief

A field you cannot fill is a unit you have not scoped. A short unit can collapse this to one paragraph, and it still names the goal, the scope, the verify command, and the report.

```
GOAL         one sentence a stranger can carry out with no chat access
SCOPE        paths this unit may write, and paths it may not
CONTEXT      files and links, pasted in full when the worker cannot open them
ACCEPTANCE   checkable lines, taste criteria included before the work starts
VERIFY       the command that proves the unit, usually cos-lint
FORBIDDEN    no sends, no purchases, no merge, no edits outside scope
REPORT       branch, PR, commands run, deviations, criteria added
STANDING     the standing orders, pasted verbatim
```

Taste criteria sit in ACCEPTANCE up front: lint clean, the right shape, the length, the reader. Do not invent the bar at the end and call it review.

## project.md

One current file per effort. Git keeps the history. Required sections, in this order:

```
# <name>

## Goal

One sentence.

## Done when

- Checkable line a stranger can mark pass or fail.

## Scope

What is in, and what is out.

## Criteria

- Taste criterion, written before the work starts.

## Criteria added
```

`Criteria added` stays empty until a criterion is discovered mid-task.

## Discovered criteria

Adopt a criterion you discover during the work, without asking, when both of these hold: it is reversible, and it is still inside the goal. Log it under `Criteria added`:

```
- YYYY-MM-DD: <criterion>
```

If it is irreversible, or it changes the goal, stop and ask Alvin.

## New deliverable type

A new deliverable type is a new folder convention or a new output kind. Before the first one lands, add a rule to that repo's `rules.yaml` with an enforcement that already passes on a fixture. A type with no rule is not a type. Prose alone does not make a type.

## Corrections

Triage each correction to the narrowest scope that would have prevented it: one surface, such as `slack`, `memo`, or `model`, or one path. Do not file it as global.

The second time the same correction shows up, promote it. Set `recurrence` to 2 or more, set `status` to `encoded`, and set `promoted_to` to a rule id that has an enforcement. Widen the scope only if the second case sat on a wider surface, and keep the new scope the narrowest one that covers the cases you have.

`cos-check-corrections` rejects a missing promotion, a broad scope, and a `promoted_to` that is not a real rule.

## One commit policy

Agents commit on a branch and open a PR. CI gates the merge. The agent does not merge, and does not commit to the default branch. One PR is one logical change.

## Sends and purchases

Nothing is sent, paid, or purchased without Alvin's approval. That covers a message sent under his name, an external email, a purchase, a payment, a deletion, and a promise to a third party. Prepare the action, then wait for an explicit yes. Reversible work inside the repo proceeds, and shows the assumption it used.

## What the checker runs

The builder does not grade the work. CI runs `cos-lint`. That applies the shared writing rules, strict mode on deliverables, the Slack shape on Slack drafts, the format checks the repo turned on, and the rules and corrections ledgers.

Slack decision shape: 2 to 4 numbered options, exactly one marked `(recommended)`, one Why line, and one default-deadline line (`If no answer by Fri, I go with 1.`). Slack drafts do not use semicolons.

Task dates, on the paths a repo configures: a hard date uses 📅 and a soft date uses ⏳, then `YYYY-MM-DD`. An optional weekday has to match the date, as in `2026-10-21 (Wed)`.

A closed task is atomic. The box is `x`, the line has one date and a receipt after `|`, and no open child is left under it.

`VLOOKUP`, `HLOOKUP`, and `XLOOKUP` are banned on the paths a repo configures. The three names cannot be removed. A repo may add further names.
