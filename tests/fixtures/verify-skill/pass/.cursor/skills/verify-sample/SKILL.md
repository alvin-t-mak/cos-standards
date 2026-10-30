---
name: verify-sample
description: "Drive the sample vault from the note, the link, and the file the script writes. Use when proving a change to the sample."
verify: scripts/verify
---

# Verify sample

## Launch

There is no server. From the repo root, run `scripts/verify`. It reads `notes/sample.md`, checks the link to `notes/build.md`, and writes `outputs/sample.txt`. Ready means that file exists and its text is `status=active`.

## Doctor

Run `scripts/verify doctor`. It exits 0 when `notes/sample.md` has `status: active` and `notes/build.md` is present. It does not write the output file.

## Drive

Run `scripts/verify`. The harness is the shell. A person does the same thing from the repo root. The end state is `outputs/sample.txt` with `status=active`, after the link check passes.

## Evidence

Copy the output file to `evidence/verify-sample/sample.txt` and keep the command output with it. The proof directory is `evidence/verify-sample`. The proof is the command and the resulting file.

## Cleanup

Run `scripts/verify cleanup`. It removes `outputs/`. Do not delete `evidence/verify-sample`.

## Helpers

The helper is `scripts/verify`. Invoke it as `scripts/verify`, `scripts/verify doctor`, or `scripts/verify cleanup`.
