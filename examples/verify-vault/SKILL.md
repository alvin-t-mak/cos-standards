---
name: verify-<app>
description: "Drive <app> from the CLI and the files it writes. Use when proving a change to <app>."
verify: <command>
---

# Verify <app>

Copy this folder to `.cursor/skills/verify-<app>/`. The folder name and `name` match. Replace every slot with a value from this repo. <app> has no UI. The surface is `<surface>`.

## Launch

There is no server to keep up. Install dependencies once. Then run `<command>` in a clean output directory. Ready means the script printed `<ready-line>` and the generated file can be opened. `<script>` is the file the command runs.

## Doctor

Run `<command> doctor` before a drive. It is read-only. It checks that `<script>` is the copy in this repo, the input notes are present, and the output directory is writable. It does not write the artifact.

## Drive

The harness is <harness>. Run `<command>` the way a person would. Open the workbook or other file it wrote and check the values. Then check that links resolve and frontmatter matches the shape this repo requires. The proof is those values.

## Evidence

Save the command output and a copy of the generated file under `<evidence-dir>`. Record the action and the values you read back.

## Cleanup

Remove the scratch output directory. Do not delete `<evidence-dir>`.

## Helpers

`<script>` is the verify command. Invoke it as `<command>`, `<command> doctor`, and `<command> cleanup`.
