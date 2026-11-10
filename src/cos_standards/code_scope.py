from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from cos_standards.errors import StandardsError

EXT = re.compile(r"\.[a-z0-9]+\Z")
SCOPE_REL = Path("standards") / "code-scope.yaml"


@dataclass(frozen=True)
class CodeScope:
    extensions: frozenset[str]
    path: Path


def bundled_scope_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "code-scope.yaml"


def read_extensions(path: Path) -> frozenset[str]:
    try:
        import yaml
    except ImportError as exc:
        raise StandardsError("PyYAML is not installed") from exc
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise StandardsError(f"{path}: {exc}") from exc
    except Exception as exc:
        raise StandardsError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise StandardsError(f"{path}: expected a mapping")
    if data.get("version") != 1:
        raise StandardsError(f"{path}: version must be 1")
    unknown = set(data) - {"version", "extensions"}
    if unknown:
        raise StandardsError(f"{path}: unknown keys {sorted(unknown)}")
    raw = data.get("extensions")
    if not isinstance(raw, list) or not raw:
        raise StandardsError(f"{path}: extensions must be a non-empty list")
    found: list[str] = []
    for item in raw:
        if not isinstance(item, str) or EXT.fullmatch(item) is None:
            raise StandardsError(f"{path}: bad extension {item!r}")
        found.append(item)
    if len(found) != len(set(found)):
        raise StandardsError(f"{path}: duplicate extension")
    return frozenset(found)


def load_code_scope(root: Path) -> CodeScope:
    bundled = bundled_scope_path()
    if not bundled.is_file():
        raise StandardsError(f"bundled code scope is missing: {bundled}")
    shared = read_extensions(bundled)
    local = (root / SCOPE_REL).resolve()
    if local.is_file() and local != bundled.resolve():
        extra = read_extensions(local)
        dropped = shared - extra
        if dropped:
            raise StandardsError(
                f"{local}: drops shared extensions {', '.join(sorted(dropped))}"
            )
        return CodeScope(extra, local)
    return CodeScope(shared, bundled)
