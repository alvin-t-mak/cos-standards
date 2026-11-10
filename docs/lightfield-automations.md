# Lightfield automations

Lightfield automations that write CRM records run with no human approval step. The merged spec is the approval, and a run does only what that spec allows (13). Numbers in parentheses cite `docs/principles.md`.

Specs live in veroa-vault under `lightfield/automations/<slug>.md`. Change a spec only through a pull request. The instructions published in Lightfield must match the spec's `## Instructions` section verbatim (3, 4).

Required headings, in this order, and the never-write floor are listed in `standards/lightfield-automation-checklist.yaml`. A spec check requires each heading as its own line, and each `never_write` phrase inside the Never write section (14, 16). A spec includes the headings below, in this order.

## Trigger

Name the one event that starts a run. Do not start the next step until that event is confirmed (12).

## Purpose

State the one outcome the run exists to produce, and keep only what a reader needs to judge that outcome (1, 5).

## May write

List every object and field the run may create or change. If an object or field is absent from this list, the run does not write it, and each entry traces to the purpose (1, 7). A spec that writes a Recruiterflow id names the field there, and the run writes it only from that run's Recruiterflow API response with a read-back.

## Never write

Copy the checklist never-write floor into the spec, and add any further refusals. That floor covers computed dollar fields, rollups, `$amount`, and Recruiterflow id fields not delivered by a Recruiterflow API response, which stay with the system that owns them, plus the Gfteams, Flexpressai, and Veroa accounts (3, 9).

## Sources

The triggering record or transcript is the only source for a value the run writes. Do not invent an id or an option value that is not in that source (8, 9).

## Skip rules

Skip the write when the match is unsure or the required evidence is missing. Name that evidence, such as a verbatim quote from the source, and leave the field unwritten (8, 9, 12).

## Idempotency

State how the run detects a duplicate before it writes, and write only the missing difference (11). A second pass over the same trigger must not create a second record.

## Read-back

Re-read every written record live from Lightfield before the next step starts (8, 12). The write call's success flag is not the receipt.

## Stop and report

If a step cannot be done exactly as the spec says, stop and report one line that starts with `stopped:`. Name the step and what was missing, and do not guess a substitute (12).

## Output

The final line lists the live record ids from the read-back (8). That line is how a reader checks the run.

## Owner

Name the person accountable for this spec. The run does not wait on their approval, because the merged spec is the approval (13).

## Kill switch

The kill switch is Pause the automation. Name that control so the owner can stop further runs without a spec change (11, 13).

## Instructions

This section is the text published in Lightfield, and the published copy must match it verbatim (3, 4). The other sections are the limits on what that text may do.
