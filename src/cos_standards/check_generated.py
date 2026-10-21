"""Diff a committed generated file against a fresh render.

`diff_generated` is the helper. `cos-check-generated` uses it on the banned mirrors.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from cos_standards.errors import StandardsError
from cos_standards.gen_banned import load_banned, markdown_path, render_json, render_md
from cos_standards.lint_writing import DATA


def diff_generated(label: str, committed: str, fresh: str) -> str:
    """Return a unified diff, or an empty string when the texts match."""
    if committed == fresh:
        return ""
    return "".join(
        difflib.unified_diff(
            committed.splitlines(keepends=True),
            fresh.splitlines(keepends=True),
            fromfile=f"{label} (committed)",
            tofile=f"{label} (generated)",
        )
    )


def check_mirrors(root: Path) -> list[str]:
    """Check the packaged json mirror, and docs/banned.md when this repo is the root."""
    problems: list[str] = []
    data = load_banned()
    json_path = DATA / "banned.json"
    if not json_path.is_file():
        problems.append("banned.json is missing. Run cos-export-banned.")
    else:
        diff = diff_generated("src/cos_standards/data/banned.json", json_path.read_text(encoding="utf-8"), render_json(data))
        if diff:
            problems.append(diff)

    source = root / "src" / "cos_standards" / "data" / "banned.yaml"
    if source.is_file():
        repo_data = load_banned(source)
        md_path = markdown_path(root)
        if not md_path.is_file():
            problems.append("docs/banned.md is missing. Run cos-export-banned.")
        else:
            diff = diff_generated("docs/banned.md", md_path.read_text(encoding="utf-8"), render_md(repo_data))
            if diff:
                problems.append(diff)
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when a generated banned mirror drifts from banned.yaml.")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        problems = check_mirrors(root)
    except StandardsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(problem, end="" if problem.endswith("\n") else "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
