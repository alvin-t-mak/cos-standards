# Orchestrate

Use this when the work outlives one agent: a stack of Slack drafts, a model plus a memo, or a research pass with several outputs. One task you can finish in this session does not need a coordinator.

You own the program. You write the briefs, drain the queue, and decide. You do not build an artifact and then grade it.

Three rules carry the rest.

- A finished unit is a queue event. Do not stop the whole program to review it inline.
- Every spawn and every resume carries the standing orders in full.
- The brief is the product. A vague brief fails quietly, because the worker cannot ask you a question.

## Roles

- **Coordinator.** Frames the work, writes briefs, drains results, and makes the calls. Does not verify a unit it also built.
- **Worker.** Builds one unit: a Slack draft, a model change, or a research note. One writer per file.
- **Verifier.** A different agent, or the CI verify job. It gets the artifact and the original ask, not the worker's explanation.

## The brief

Every spawn carries all of this. A field you cannot fill is a unit you have not scoped.

```
GOAL         one sentence, the outcome, executable by a stranger
SCOPE        paths this unit may write, and paths it may not
CONTEXT      files and prior results this unit needs, pasted in full
ACCEPTANCE   checkable criteria, one per line
VERIFY       the command, or the checker, and that the builder does not run it
TIMEBOX      stop and return partial findings when this runs out
FORBIDDEN    no external sends, no payments, no merges, plus unit-specific bans
REPORT       status, what you ran, receipts, deviations, follow-ups
STANDING     the standing orders below, pasted in full
```

A one-command unit can collapse this to a short paragraph that still names the goal, the scope, the verify command, and the report shape.

## STANDING ORDERS

Every agent follows these. Paste them into every brief and every resume.

<!-- rule: standing-run-linters -->
1. Run `cos-lint` before you hand work back. The verify job runs `cos-verify`.

<!-- rule: standing-never-self-verify -->
2. Never verify your own work. A different agent, or the CI verify job, checks the artifact. The verifier, not the builder, appends corrections.

<!-- rule: standing-two-sources -->
3. Two sources for any important number, or label it unverified.

<!-- rule: standing-no-external -->
4. Never send anything external without approval. That includes Slack, email, CRM writes, and payments.

<!-- rule: standing-escalate -->
5. Do not merge a destructive folder move without a yes.

## Steps

1. **Frame.** State what done looks like in a way you can count. If one agent can finish it here, do that and skip the rest.
2. **Pilot.** Run one unit through brief, worker, and verifier before you fan out.
3. **Scale.** Refill as workers finish. Do not batch them so the slowest one blocks the rest.
4. **Drain.** Record each result, then spawn the next wave. Do not review a diff inside the drain.
5. **Close.** Every unit has a result. The verifier's receipt matches the current artifact. Corrections follow the section below.

## Commit

Agents commit on a branch and open a pull request. CI gates the merge.

## Projects

Every project is `projects/<name>/project.md`. It names the ask, the stakeholder, the done-when, the taste criteria, and links to the artifacts. Dates live in front matter, not in folder names.

Checks key off file-name patterns (`*.slack.md`, `*.prospects.csv`), not folders.

A new deliverable type defines done-when as checkable items in the brief. The verifier, not the builder, writes the check.

Taste criteria are written in the brief before work starts.

If an agent finds a criterion that is not in the brief, that would improve the result, and that is reversible and inside the goal, it adopts the criterion and adds one line under `Criteria added` in `project.md`. It asks only when the change would move the scope, who is contacted, or anything external or irreversible.

## Corrections

Each correction from the owner goes to the narrowest scope: that `project.md`, the deliverable-type rules, or global standards. Promote one level when the same correction shows up in a second place. The verifier appends it to `standards/corrections.yaml` and states in one line where it went.
