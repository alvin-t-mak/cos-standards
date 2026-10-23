from __future__ import annotations

from pathlib import Path


def package_repo() -> Path:
    candidate = Path(__file__).resolve().parents[2]
    marker = candidate / "src" / "cos_standards" / "data" / "rules.yaml"
    if marker.is_file():
        return candidate
    return Path.cwd()
