from __future__ import annotations

import datetime as dt
import os
import re
import sys
from pathlib import Path

from cos_standards.paths import package_repo

WALK_SKIP = {".git", "__pycache__", ".pytest_cache"}
TASK = re.compile(r"^\s*- \[[ xX]\]")
MARKER = re.compile(r"[📅⏳✅]")
ISO = re.compile(r"[ \t]*(\d{4}-\d{2}-\d{2})\b")
DAY_LABEL = re.compile(
    r"(?i)(\b(?:light|buffer|weekend)\s+days?\b|"
    r"\b(?:mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
    r"\s*[:(\-–]\s*(?:light|buffer|weekend)\b)"
)
DATE_STAMP = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b")
VENDOR_NAME = "Vendor Notes.md"
MAX_BULLETS = 4
MAX_WORDS = 25
DEFAULT_NOTION_PREFIXES = (
    "Product/",
    "Ops/Leadership Meetings/",
)
DEFAULT_NOTION_FILES = {"Website/Website Execution Checklist.md"}


def strip_fences(text: str) -> str:
    out = []
    fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fence = not fence
            out.append("")
            continue
        out.append("" if fence else line)
    return "\n".join(out)


def _valid_date(value: str) -> bool:
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _marker_problem(rest: str) -> str | None:
    found = ISO.match(rest)
    if found:
        if _valid_date(found.group(1)):
            return None
        return f"malformed date {found.group(1)}"
    if re.match(r"[ \t]*($|[📅⏳✅])", rest):
        return "date marker needs YYYY-MM-DD"
    if re.match(r"[ \t]*[\d/]", rest):
        return "malformed date"
    if re.match(r"[ \t]*[A-Za-z]", rest):
        return "malformed date"
    return None


def task_date_problems(rel: str, text: str) -> list[str]:
    out = []
    for i, line in enumerate(strip_fences(text).splitlines(), 1):
        if not TASK.match(line):
            continue
        for match in MARKER.finditer(line):
            problem = _marker_problem(line[match.end() :])
            if problem:
                out.append(f"{rel}:{i}: {problem}")
    return out


def _frontmatter(text: str) -> str:
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    return match.group(1) if match else ""


def _closed_status_line(text: str) -> tuple[bool, bool]:
    body = text.split("---", 2)[-1] if text.startswith("---") else text
    match = re.search(r"(?m)^## Status[ \t]*\n(.*?)(?=^## |\Z)", body, re.S)
    if not match:
        return False, False
    content = []
    for line in match.group(1).splitlines():
        if not line.strip():
            if content:
                break
            continue
        content.append(line.strip())
    if not content:
        return False, False
    mentions = any(line.startswith("CLOSED:") for line in content)
    one_line = len(content) == 1 and content[0].startswith("CLOSED:")
    return mentions, one_line


def atomic_close_problems(rel: str, text: str) -> list[str]:
    fm = _frontmatter(text)
    status_match = re.search(r"(?m)^status:\s*([A-Za-z0-9_-]+)", fm)
    closed_match = re.search(r"(?m)^closed:\s*(\S+)", fm)
    status = status_match.group(1) if status_match else ""
    closed = closed_match.group(1) if closed_match else ""
    mentions, one_line = _closed_status_line(text)
    if status != "closed" and not closed and not mentions:
        return []
    out = []
    if status != "closed":
        out.append(f"{rel}: closed bundle needs status: closed")
    if not _valid_date(closed):
        out.append(f"{rel}: closed bundle needs closed: YYYY-MM-DD")
    if not one_line:
        out.append(f"{rel}: closed bundle needs a one-line CLOSED: status")
    if not re.search(r"(?m)^\s*- \[x\]", text, re.I):
        out.append(f"{rel}: closed bundle needs a ticked box")
    return out


def vendor_notes_problems(
    text: str,
    rel: str = VENDOR_NAME,
    max_bullets: int = MAX_BULLETS,
    max_words: int = MAX_WORDS,
) -> list[str]:
    out = []
    for part in re.split(r"(?m)^### ", text)[1:]:
        title = part.splitlines()[0].strip() if part.splitlines() else ""
        body = re.split(r"(?m)^## ", part, maxsplit=1)[0]
        bullets = [line for line in body.splitlines() if line.startswith("- ")]
        if len(bullets) > max_bullets:
            out.append(f"{rel}: {title}: {len(bullets)} bullets, max {max_bullets}")
        for line in bullets:
            words = re.findall(r"\S+", line[2:])
            if len(words) > max_words:
                out.append(f"{rel}: {title}: {len(words)} words, max {max_words}")
            if DATE_STAMP.search(line):
                out.append(f"{rel}: {title}: no date stamps")
    return out


def notion_scope(
    prefixes: tuple[str, ...] | None = None,
    files: set[str] | None = None,
) -> tuple[tuple[str, ...], set[str]]:
    merged_prefixes = tuple(dict.fromkeys((*DEFAULT_NOTION_PREFIXES, *(prefixes or ()))))
    merged_files = set(DEFAULT_NOTION_FILES) | set(files or ())
    return merged_prefixes, merged_files


def notion_day_problems(
    rel: str,
    text: str,
    prefixes: tuple[str, ...] | None = None,
    files: set[str] | None = None,
) -> list[str]:
    prefixes, files = notion_scope(prefixes, files)
    if rel not in files and not rel.startswith(prefixes):
        return []
    out = []
    for i, line in enumerate(strip_fences(text).splitlines(), 1):
        if DAY_LABEL.search(line):
            out.append(f"{rel}:{i}: do not label a day light, buffer, or weekend")
    return out


def _kept_dir(name: str) -> bool:
    return name not in WALK_SKIP and not name.endswith(".egg-info")


def merge_cell_problems(root: Path) -> list[str]:
    out = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if _kept_dir(d))
        for name in sorted(files):
            if not (name.startswith("build_") and name.endswith(".py")):
                continue
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            if rel.startswith("Archive/") or "/outputs/" in f"/{rel}":
                continue
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "merge_cells" in line.split("#", 1)[0]:
                    out.append(f"{rel}:{i}: do not merge cells")
    return out


def iter_markdown(root: Path):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if _kept_dir(d))
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            if rel.startswith("outputs/") or "/outputs/" in f"/{rel}":
                continue
            yield path, rel


def split_notion(paths: list[str]) -> tuple[tuple[str, ...], set[str]]:
    prefixes: list[str] = []
    files: set[str] = set()
    for item in paths:
        norm = str(item).strip().replace("\\", "/").lstrip("/")
        if not norm:
            continue
        if norm.endswith(".md"):
            files.add(norm)
        else:
            if not norm.endswith("/"):
                norm += "/"
            prefixes.append(norm)
    return tuple(prefixes), files


def _is_vendor(rel: str, extra: set[str]) -> bool:
    return rel.rsplit("/", 1)[-1] == VENDOR_NAME or rel in extra


def problems(
    root: Path | None = None,
    *,
    notion_paths: list[str] | None = None,
    vendor_paths: list[str] | None = None,
    max_bullets: int = MAX_BULLETS,
    max_words: int = MAX_WORDS,
) -> list[str]:
    root = root or package_repo()
    extra_prefixes, extra_files = split_notion(list(notion_paths or []))
    prefixes, notion_files = notion_scope(extra_prefixes, extra_files)
    extra_vendor = {str(item).strip().replace("\\", "/").lstrip("/") for item in (vendor_paths or []) if str(item).strip()}
    found: list[str] = []
    found.extend(merge_cell_problems(root))
    seen: set[str] = set()
    for path, rel in iter_markdown(root):
        seen.add(rel)
        text = path.read_text(encoding="utf-8")
        found.extend(task_date_problems(rel, text))
        found.extend(atomic_close_problems(rel, text))
        found.extend(notion_day_problems(rel, text, prefixes, notion_files))
        if _is_vendor(rel, extra_vendor):
            found.extend(vendor_notes_problems(text, rel, max_bullets, max_words))
    for rel in sorted(extra_vendor - seen):
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        found.extend(vendor_notes_problems(text, rel, max_bullets, max_words))
    return found


def main(argv: list[str] | None = None) -> int:
    root = Path(argv[0]) if argv else package_repo()
    found = problems(root)
    if found:
        print(f"{len(found)} formatting problem(s)")
        for item in found:
            print(" ", item)
        return 1
    print("format ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
