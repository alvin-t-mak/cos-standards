"""Load cos.yaml or standards/local.yaml.

A consuming repo may add paths, banned terms, and ledger rules, and it may
set a stricter cap. It cannot turn a check off. A path that is not in the
repo adds nothing, and the check still runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cos_standards.errors import StandardsError
from cos_standards.lint_format import MAX_BULLETS, MAX_WORDS
from cos_standards.lint_shape import MAX_LINES_LIMIT
from cos_standards.lint_writing import HERE, compile_rules, read_rule_document

DENY_KEYS = {
    "disable",
    "disabled",
    "disables",
    "enabled",
    "exempt",
    "exemption",
    "exemptions",
    "except",
    "exception",
    "exceptions",
    "generated",
    "ignore_rule",
    "ignore_rules",
    "ignored_rules",
    "omit",
    "omit_logo",
    "override",
    "overrides",
    "override_rules",
    "remove",
    "remove_rules",
    "removed_rules",
    "drop_rules",
    "skip",
    "skip_rule",
    "skip_rules",
    "strict",
    "waive",
    "waiver",
    "waivers",
}
ROOT_KEYS = {
    "version",
    "extra_banned",
    "extra_banned_file",
    "rules",
    "corrections",
    "models",
    "notion_paths",
    "vendor_notes",
    "slack",
    "outward",
    "formula_style_prefixes",
}
SEARCH = ("cos.yaml", "standards/local.yaml")


@dataclass
class Config:
    root: Path
    config_path: Path | None
    rules: list[dict]
    banned_ids: set[str]
    rules_path: Path | None
    corrections_path: Path | None
    models_path: Path | None
    notion_paths: list[str]
    vendor_paths: list[str]
    vendor_max_bullets: int
    vendor_max_words: int
    slack_max_lines: int
    outward_folders: list[str]
    outward_terms: list[str]
    formula_style_prefixes: list[str]
    raw: dict = field(repr=False)


def reject_weakening(node: object, path: str = "$") -> None:
    """Raise if a config tries to disable or exempt a shared check."""
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key).casefold() in DENY_KEYS:
                raise StandardsError(
                    f"{path}.{key}: local config cannot disable, skip, waive, or exempt a shared check"
                )
            reject_weakening(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            reject_weakening(value, f"{path}[{index}]")


def find_config(explicit: str | None, root: Path) -> Path | None:
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = root / path
        if not path.is_file():
            raise StandardsError(f"config not found: {path}")
        return path
    for relative in SEARCH:
        path = root / relative
        if path.is_file():
            return path
    return None


def empty_config(root: Path) -> Config:
    shared = read_rule_document(Path(HERE) / "banned.yaml")["rules"]
    compiled = compile_rules(shared, str(Path(HERE) / "banned.yaml"))
    return Config(
        root=root,
        config_path=None,
        rules=compiled,
        banned_ids={rule["id"] for rule in compiled},
        rules_path=None,
        corrections_path=None,
        models_path=None,
        notion_paths=[],
        vendor_paths=[],
        vendor_max_bullets=MAX_BULLETS,
        vendor_max_words=MAX_WORDS,
        slack_max_lines=MAX_LINES_LIMIT,
        outward_folders=[],
        outward_terms=[],
        formula_style_prefixes=[],
        raw={},
    )


def load_config(explicit: str | None, root: Path, *, check_paths: bool = True) -> Config:
    del check_paths  # paths that are absent add nothing; existence is not an error
    root = root.resolve()
    config_path = find_config(explicit, root)
    if config_path is None:
        return empty_config(root)
    raw = _read_yaml(config_path)
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise StandardsError(f"{config_path}: expected a mapping")
    reject_weakening(raw)
    unknown = set(raw) - ROOT_KEYS
    if unknown:
        raise StandardsError(f"{config_path}: unknown keys {sorted(unknown)}")
    if raw.get("version") != 1:
        raise StandardsError(f"{config_path}: version must be 1")

    slack = _section(raw.get("slack"), "slack", {"max_lines"})
    max_lines = _cap(slack.get("max_lines", MAX_LINES_LIMIT), "slack.max_lines", 1, MAX_LINES_LIMIT)

    vendor = _section(raw.get("vendor_notes"), "vendor_notes", {"paths", "max_bullets", "max_words"})
    vendor_paths = _string_list(vendor.get("paths", []), "vendor_notes.paths")
    max_bullets = _cap(vendor.get("max_bullets", MAX_BULLETS), "vendor_notes.max_bullets", 1, MAX_BULLETS)
    max_words = _cap(vendor.get("max_words", MAX_WORDS), "vendor_notes.max_words", 1, MAX_WORDS)

    outward = _section(raw.get("outward"), "outward", {"folders", "terms"})
    folders = _string_list(outward.get("folders", []), "outward.folders")
    terms = _string_list(outward.get("terms", []), "outward.terms")

    notion_paths = _string_list(raw.get("notion_paths", []), "notion_paths")
    prefixes = _string_list(raw.get("formula_style_prefixes", []), "formula_style_prefixes")

    rules_path = _optional_path(raw.get("rules"), root, "rules")
    corrections_path = _optional_path(raw.get("corrections"), root, "corrections")
    models_path = _optional_path(raw.get("models"), root, "models")

    extra_raw = _extra_banned(raw, root)
    shared = read_rule_document(Path(HERE) / "banned.yaml")["rules"]
    shared_ids = {rule.get("id") for rule in shared}
    seen: set[str] = set()
    for rule in extra_raw:
        rule_id = rule.get("id") if isinstance(rule, dict) else None
        if rule_id in shared_ids:
            raise StandardsError(
                f"extra rule {rule_id} collides with a shared rule. Shared rules cannot be replaced."
            )
        if rule_id in seen:
            raise StandardsError(f"extra rule {rule_id} is duplicated")
        if rule_id:
            seen.add(rule_id)
    compiled = compile_rules(shared + extra_raw, f"{Path(HERE) / 'banned.yaml'} + {config_path}")
    return Config(
        root=root,
        config_path=config_path,
        rules=compiled,
        banned_ids={rule["id"] for rule in compiled},
        rules_path=rules_path,
        corrections_path=corrections_path,
        models_path=models_path,
        notion_paths=notion_paths,
        vendor_paths=vendor_paths,
        vendor_max_bullets=max_bullets,
        vendor_max_words=max_words,
        slack_max_lines=max_lines,
        outward_folders=folders,
        outward_terms=terms,
        formula_style_prefixes=prefixes,
        raw=raw,
    )


def _extra_banned(raw: dict, root: Path) -> list[dict]:
    inline = raw.get("extra_banned", [])
    if not isinstance(inline, list):
        raise StandardsError("extra_banned must be a list")
    rules = list(inline)
    file_value = raw.get("extra_banned_file")
    if file_value is not None:
        path = _optional_path(file_value, root, "extra_banned_file")
        if path is not None and path.is_file():
            document = read_rule_document(path)
            rules.extend(document["rules"])
    for rule in rules:
        if not isinstance(rule, dict):
            raise StandardsError("extra_banned entries must be mappings")
    return rules


def _section(value: object, label: str, allowed: set[str]) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise StandardsError(f"{label} must be a mapping")
    unknown = set(value) - allowed
    if "allow" in unknown and label == "outward":
        raise StandardsError("outward.allow cannot be set")
    if unknown:
        raise StandardsError(f"{label}: unknown keys {sorted(unknown)}")
    return value


def _string_list(value: object, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise StandardsError(f"{label} must be a list of strings")
    return list(value)


def _optional_path(value: object, root: Path, label: str) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise StandardsError(f"{label} must be a path")
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path


def _cap(value: object, label: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or isinstance(value, float):
        raise StandardsError(f"{label} must be an integer from {low} to {high}")
    if not low <= value <= high:
        raise StandardsError(f"{label} must be an integer from {low} to {high}")
    return value


def _read_yaml(path: Path) -> object:
    try:
        import yaml
    except ImportError as exc:
        raise StandardsError("PyYAML is not installed") from exc
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise StandardsError(f"{path}: {exc}") from exc
