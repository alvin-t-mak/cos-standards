# Build the sample file

A person runs the script and checks the file it writes.

## Sub-features

- Read `notes/sample.md` and require `status: active`.
- Follow the link to `notes/build.md`.
- Write `outputs/sample.txt`.

## How to get to it (user POV)

From the repo root, run `scripts/verify`.

## Driving it with shell

Run `scripts/verify`. The end state is `outputs/sample.txt` containing `status=active`, and the same text in `evidence/verify-sample/sample.txt`.

## Gotchas

If `notes/build.md` is missing, the drive fails. Record that here. Do not skip the link check to make the run pass.
