"""Lint markdown, text, Python, and HTML in a repo.

Skips generated banned mirrors, Slack style (it quotes banned text), and
output folders. cos-lint always runs this strict: a warning fails.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from cos_standards.lint_writing import CODE_EXTS, TEXT_EXTS, main as writing_main

SKIP_FILES = {
    "docs/banned.md",
    "docs/slack-style.md",
    "standards/banned.md",
    "standards/slack-style.md",
}
WALK_SKIP = {".git", "__pycache__", ".pytest_cache"}


def keep(root: Path, path: Path) -> bool:
    ext = path.suffix.lower()
    if ext not in TEXT_EXTS and ext not in CODE_EXTS:
        return False
    rel = path.relative_to(root).as_posix()
    if rel.startswith("outputs/") or "/outputs/" in f"/{rel}":
        return False
    if rel in SKIP_FILES:
        return False
    return True


def collect(root: Path) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in WALK_SKIP and not d.endswith(".egg-info"))
        for name in sorted(files):
            path = Path(dirpath) / name
            if keep(root, path):
                found.append(path)
    return found


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Lint repo deliverables for banned writing.")
    ap.add_argument("paths", nargs="*", help="files or directories; default is the working directory")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--errors-only", action="store_true", help="hide warnings")
    args = ap.parse_args(argv)
    root = Path.cwd()
    if args.paths:
        files = []
        for raw in args.paths:
            path = Path(raw)
            if path.is_dir():
                files.extend(str(item) for item in collect(path))
            elif path.is_file():
                files.append(str(path))
    else:
        files = [str(path) for path in collect(root)]
    if not files:
        return 0
    extra = []
    if args.strict:
        extra.append("--strict")
    if args.errors_only:
        extra.append("--errors-only")
    return writing_main(extra + files)


if __name__ == "__main__":
    sys.exit(main())
