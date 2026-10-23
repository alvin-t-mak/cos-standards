from __future__ import annotations

import sys
from pathlib import Path

from cos_standards.paths import package_repo

TEXT_EXTS = {".md", ".txt", ".html", ".htm"}
REJECTED = {"allow", "omit_logo", "enabled", "exempt", "exemption", "skip"}


def problems(data: dict | None = None, root: Path | None = None) -> list[str]:
    root = root or package_repo()
    data = data if data is not None else {"folders": [], "terms": []}
    if not isinstance(data, dict):
        return ["outward config must be a mapping"]
    rejected = sorted(set(data) & REJECTED)
    if rejected:
        return [f"outward config cannot set {', '.join(rejected)}"]
    folders = data.get("folders") or []
    terms = data.get("terms") or []
    if not isinstance(folders, list) or not isinstance(terms, list):
        return ["outward folders and terms must be lists"]
    if not folders:
        return []
    needles = [str(term).casefold() for term in terms if str(term).strip()]
    found = []
    for folder in folders:
        base = root / str(folder)
        if not base.is_dir():
            found.append(f"missing outward folder: {folder}")
            continue
        if not needles:
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTS:
                continue
            rel = path.relative_to(root).as_posix()
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for i, line in enumerate(lines, 1):
                folded = line.casefold()
                if any(needle in folded for needle in needles):
                    found.append(f"{rel}:{i}")
    return found


def main(argv: list[str] | None = None) -> int:
    del argv
    found = problems()
    if found:
        print(f"{len(found)} outward name hit(s)")
        for item in found:
            print(" ", item)
        return 1
    print("outward names ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
