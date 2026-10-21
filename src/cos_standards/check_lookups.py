"""Fail if a build script contains VLOOKUP(, HLOOKUP(, or XLOOKUP(."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from cos_standards.paths import package_repo

CALL = re.compile(r"\b(VLOOKUP|HLOOKUP|XLOOKUP)\s*\(")
WALK_SKIP = {".git", "__pycache__", ".pytest_cache"}


def problems(root: Path | None = None) -> list[str]:
    root = root or package_repo()
    found = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in WALK_SKIP and not d.endswith(".egg-info"))
        for name in sorted(files):
            if not (name.startswith("build_") and name.endswith(".py")):
                continue
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            if rel.startswith("Archive/") or "/outputs/" in f"/{rel}":
                continue
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                code = line.split("#", 1)[0]
                if CALL.search(code):
                    found.append(f"{rel}:{i}: {line.strip()}")
    return found


def main(argv: list[str] | None = None) -> int:
    root = Path(argv[0]) if argv else package_repo()
    found = problems(root)
    if found:
        print(f"{len(found)} lookup call(s)")
        for item in found:
            print(" ", item)
        return 1
    print("lookups ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
