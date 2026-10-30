# Links and frontmatter

A person follows links in the notes and trusts the frontmatter.

## Sub-features

- Every markdown link in the notes for <app> points at a file that exists.
- Frontmatter keys match the shape this repo requires.

## How to get to it (user POV)

Open a note, read its frontmatter, and follow a link.

## Driving it with <harness>

Run `<command>` and include the link and frontmatter checks in that same command. A broken link fails the drive. Record the result under `<evidence-dir>`.

## Gotchas

A link that only works from one directory is still a broken link. Record the path you started from. Do not drop the check to make the run pass.
