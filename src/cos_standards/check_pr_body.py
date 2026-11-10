from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from cos_standards.code_scope import load_code_scope
from cos_standards.errors import StandardsError

REQUIRED = ("Why", "Scope", "Blast radius", "Verification")
COMPARE_FILE_CAP = 300
HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def problems(body: str, paths: list[str], root: Path) -> list[str]:
    scope = load_code_scope(root)
    changed = code_paths(paths, scope.extensions)
    if not changed:
        return []
    present = headings(body)
    missing = [name for name in REQUIRED if name.casefold() not in present]
    if not missing:
        return []
    shown = ", ".join(changed[:8])
    if len(changed) > 8:
        shown += f" (+{len(changed) - 8} more)"
    return [f"code change ({shown}) needs PR headings: {', '.join(missing)}"]


def code_paths(paths: list[str], extensions: frozenset[str]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        path = raw.strip().replace("\\", "/")
        if not path or path in seen:
            continue
        seen.add(path)
        if Path(path).suffix.lower() in extensions:
            found.append(path)
    return found


def headings(body: str) -> set[str]:
    found: set[str] = set()
    fenced = False
    for line in body.splitlines():
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING.match(line.strip())
        if match is None:
            continue
        found.add(_heading_key(match.group(1)))
    return found


def paths_from_compare(data: object) -> list[str]:
    if not isinstance(data, dict):
        raise StandardsError("compare response must be a mapping")
    files = data.get("files")
    if files is None and isinstance(data.get("message"), str):
        raise StandardsError(str(data["message"]))
    if files is None:
        files = []
    if not isinstance(files, list):
        raise StandardsError("compare response has no files list")
    if len(files) >= COMPARE_FILE_CAP:
        raise StandardsError(
            f"compare file list stopped at {COMPARE_FILE_CAP} paths. Split the pull request."
        )
    found: list[str] = []
    for item in files:
        if not isinstance(item, dict):
            raise StandardsError("compare file entry must be a mapping")
        name = item.get("filename")
        if not isinstance(name, str) or not name.strip():
            raise StandardsError("compare file entry needs a filename")
        found.append(name)
        previous = item.get("previous_filename")
        if isinstance(previous, str) and previous.strip():
            found.append(previous)
    return found


def body_from_event(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StandardsError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise StandardsError(f"{path}: expected a mapping")
    pull = data.get("pull_request")
    if not isinstance(pull, dict):
        raise StandardsError(f"{path}: no pull_request")
    body = pull.get("body")
    if body is None:
        return ""
    if not isinstance(body, str):
        raise StandardsError(f"{path}: pull_request.body is not text")
    return body


def _heading_key(text: str) -> str:
    trimmed = re.sub(r"\s+#+\s*$", "", text.strip())
    return re.sub(r"\s+", " ", trimmed).casefold()


def _read_body(event: str | None, body_file: str | None) -> str:
    if event and body_file:
        raise StandardsError("pass --event or --body-file, not both")
    if event:
        return body_from_event(Path(event))
    if body_file:
        path = Path(body_file)
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise StandardsError(f"{path}: {exc}") from exc
    raise StandardsError("pass --event or --body-file")


def _read_paths(compare_file: str | None, paths_file: str | None) -> list[str]:
    if compare_file and paths_file:
        raise StandardsError("pass --compare-file or --paths-file, not both")
    if compare_file:
        path = Path(compare_file)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StandardsError(f"{path}: {exc}") from exc
        return paths_from_compare(data)
    if paths_file:
        path = Path(paths_file)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise StandardsError(f"{path}: {exc}") from exc
        return [line.strip() for line in text.splitlines() if line.strip()]
    raise StandardsError("pass --compare-file or --paths-file")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when a code change is missing PR headings.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--event", help="GitHub event JSON. Reads pull_request.body.")
    parser.add_argument("--body-file")
    parser.add_argument("--compare-file", help="GitHub compare API JSON. Reads files[].filename.")
    parser.add_argument("--paths-file", help="Changed paths, one per line.")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        body = _read_body(args.event, args.body_file)
        paths = _read_paths(args.compare_file, args.paths_file)
        found = problems(body, paths, root)
    except StandardsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if found:
        print(f"{len(found)} pull request problem(s)")
        for item in found:
            print(f" {item}")
        return 1
    print("pr body ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
