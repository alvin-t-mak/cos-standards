from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from cos_standards.paths import package_repo

DRAFT_EXTS = {".md", ".txt", ".markdown"}
COMMENT_ONLY = re.compile(r"^\s*<!--.*-->\s*$")
OPTION = re.compile(r"^\s*\d+\.\s+\S")
WHY = re.compile(r"^\s*Why\b")
DEFAULT_WHEN = re.compile(
    r"(?i)\b(deadline|due|by|eod|today|tomorrow|mon|tue|wed|thu|fri|sat|sun)\b"
)
DEFAULT_ACT = re.compile(r"(?i)(if no answer|i go with|i'll go with|\bdefault\b)")
STAR_BULLET = re.compile(r"^\s*(?:\*\s+|•\s+)")
SKIP_NAMES = {"readme.md", ".gitkeep"}
WALK_SKIP = {".git", "__pycache__", ".pytest_cache"}
MAX_LINES_LIMIT = 5


def is_draft(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1].lower()
    return name.endswith((".slack.md", ".slack.txt", ".slack.markdown"))


def has_default_deadline(lines: list[str]) -> bool:
    return any(DEFAULT_WHEN.search(line) and DEFAULT_ACT.search(line) for line in lines)


def surface_problems(rel: str, lines: list[str]) -> list[str]:
    out = []
    if any(";" in line for line in lines):
        out.append(f"{rel}: no semicolons in a Slack draft")
    if any(STAR_BULLET.match(line) for line in lines):
        out.append(f"{rel}: use - bullets in a Slack draft")
    return out


def content_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        if not line.strip() or COMMENT_ONLY.match(line):
            continue
        lines.append(line)
    return lines


def is_decision(rel: str, text: str) -> bool:
    if "decision" in rel.lower():
        return True
    if "<!-- decision-request -->" in text:
        return True
    return any("(recommended)" in line for line in text.splitlines())


def problems_for(rel: str, text: str, max_lines: int = MAX_LINES_LIMIT) -> list[str]:
    lines = content_lines(text)
    if is_decision(rel, text):
        options = [line for line in lines if OPTION.match(line)]
        marked = [line for line in options if "(recommended)" in line]
        out = []
        if len(options) < 2:
            out.append(f"{rel}: decision request needs at least two numbered options")
        if len(marked) != 1:
            out.append(f"{rel}: mark exactly one option (recommended)")
        if not any(WHY.match(line) for line in lines):
            out.append(f"{rel}: decision request needs a line that starts with Why")
        if not has_default_deadline(lines):
            out.append(f"{rel}: decision request needs a default-deadline line")
        return surface_problems(rel, lines) + out
    if len(lines) > max_lines:
        return surface_problems(rel, lines) + [f"{rel}: {len(lines)} lines, Slack drafts allow {max_lines}"]
    return surface_problems(rel, lines)


def collect(root: Path) -> list[Path]:
    found = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in WALK_SKIP and not d.endswith(".egg-info"))
        for name in sorted(files):
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            if "/outputs/" in f"/{rel}" or rel.startswith("outputs/"):
                continue
            if path.suffix.lower() not in DRAFT_EXTS:
                continue
            if path.name.lower() in SKIP_NAMES:
                continue
            if is_draft(rel):
                found.append(path)
    return found


def problems(root: Path | None = None, max_lines: int = MAX_LINES_LIMIT) -> list[str]:
    root = root or package_repo()
    found = []
    for path in collect(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        found.extend(problems_for(rel, text, max_lines=max_lines))
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check Slack draft shape.")
    ap.add_argument("root", nargs="?", default=None)
    args = ap.parse_args(argv)
    root = Path(args.root) if args.root else package_repo()
    found = problems(root)
    if found:
        print(f"{len(found)} Slack shape problem(s)")
        for item in found:
            print(" ", item)
        return 1
    print("slack shape ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
