---
name: verify-<app>
description: "Drive <app> the way a user does, on the <surface>. Use when proving a change to <app>."
verify: <command>
---

# Verify <app>

Copy this folder to `.cursor/skills/verify-<app>/`. The folder name and `name` match. Replace every slot with a value from this repo.

## Launch

Start <app> with `<command>` from the repo root. Wait until the output contains `<ready-line>`. Ready means a person can use <app>, including migrations and seed data. Tear the process down when the drive is finished. For a short-lived CLI, launch means install dependencies once, then start each drive in its own session. `<script>` is the file the command runs.

## Doctor

Run `<command> doctor` before a drive. It is read-only. It checks that the process is up, the build is this checkout, the port belongs to this run, and auth is valid. For a CLI with no process, it checks that `<script>` exists and the working directory is writable.

## Drive

Use the <harness> harness. Prefer stable handles from this repo (labels, prompt strings, route paths) over coordinates and tab order. The commands below are the ones a person runs.

## Evidence

Exercise the real user path. Capture the action and the state after it, and check side effects. Mocks stay at the boundary the production app already uses. Write the proof under `<evidence-dir>`.

## Cleanup

Stop only the process this run started. Remove scratch state. Do not delete `<evidence-dir>`.

## Helpers

`<script>` is the verify command. Invoke it as `<command>`, `<command> doctor`, `<command> drive`, and `<command> cleanup`.
