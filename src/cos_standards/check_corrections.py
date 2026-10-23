from __future__ import annotations

import sys
from pathlib import Path

import yaml

from cos_standards.errors import StandardsError


def problems(data: dict) -> list[str]:
    items = data.get("corrections")
    if items is None:
        return ["corrections.yaml needs a corrections list"]
    if not isinstance(items, list):
        return ["corrections must be a list"]
    out = []
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict):
            out.append(f"entry {i} is not a mapping")
            continue
        if not item.get("id") or not item.get("note"):
            out.append(f"entry {i} needs id and note")
        try:
            count = int(item.get("count"))
        except (TypeError, ValueError):
            out.append(f"entry {i} needs an integer count")
            continue
        if count >= 2 and not item.get("check"):
            out.append(f"{item.get('id')}: seen {count} times with no check id")
    return out


def check_file(path: Path | None) -> list[str]:
    if path is None or not path.is_file():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise StandardsError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        return [f"{path}: corrections file needs a mapping"]
    return [f"{path}: {item}" for item in problems(data)]


def main(argv: list[str] | None = None) -> int:
    path = Path(argv[0]) if argv else None
    try:
        found = check_file(path)
    except StandardsError as exc:
        print(f"corrections check failed: {exc}", file=sys.stderr)
        return 2
    if found:
        print(f"{len(found)} correction problem(s)")
        for item in found:
            print(" ", item)
        return 1
    print("corrections ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
