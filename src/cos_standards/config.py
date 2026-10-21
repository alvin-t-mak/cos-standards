"""Load cos.yaml or standards/local.yaml.

Local config may add rules, paths, and repo-specific banned terms.
It may not disable, replace, skip, waive, or exempt a shared rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cos_standards.errors import StandardsError
from cos_standards.lint_format import IDENT_RE
from cos_standards.lint_writing import DATA, compile_rules, read_rule_document

DENY_KEYS = {
    "disable",
    "disabled",
    "disables",
    "exempt",
    "exemption",
    "exemptions",
    "except",
    "exception",
    "exceptions",
    "ignore_rule",
    "ignore_rules",
    "ignored_rules",
    "skip",
    "skip_rule",
    "skip_rules",
    "waive",
    "waiver",
    "waivers",
    "override",
    "overrides",
    "override_rules",
    "remove",
    "remove_rules",
    "removed_rules",
    "drop_rules",
}
ROOT_KEYS = {
    "version",
    "paths",
    "extra_banned",
    "extra_banned_file",
    "deliverables",
    "slack",
    "format",
    "project",
    "rules",
    "corrections",
    "generated",
}
SEARCH = ("cos.yaml", "standards/local.yaml")


@dataclass
class Config:
    root: Path
    config_path: Path
    paths: list[Path]
    deliverable_paths: list[Path]
    slack_paths: list[Path]
    rules: list[dict]
    banned_ids: set[str]
    rules_path: Path | None
    corrections_path: Path | None
    dates_enabled: bool
    dates_paths: list[Path]
    require_weekday: bool
    atomic_enabled: bool
    atomic_paths: list[Path]
    lookups_enabled: bool
    lookup_paths: list[Path]
    extra_lookups: tuple[str, ...]
    project_paths: list[Path]
    generated: bool
    raw: dict = field(repr=False)


def reject_weakening(node: object, path: str = "$") -> None:
    """Raise if a config tries to disable or exempt a shared rule."""
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key).casefold() in DENY_KEYS:
                raise StandardsError(
                    f"{path}.{key}: local config cannot disable, skip, waive, or exempt a shared rule"
                )
            reject_weakening(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            reject_weakening(value, f"{path}[{index}]")


def find_config(explicit: str | None, root: Path) -> Path:
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
    raise StandardsError("no config found. Add cos.yaml or standards/local.yaml, or pass --config.")


def load_config(explicit: str | None, root: Path, *, check_paths: bool = True) -> Config:
    root = root.resolve()
    config_path = find_config(explicit, root)
    raw = _read_yaml(config_path)
    if not isinstance(raw, dict):
        raise StandardsError(f"{config_path}: expected a mapping")
    reject_weakening(raw)
    unknown = set(raw) - ROOT_KEYS
    if unknown:
        raise StandardsError(f"{config_path}: unknown keys {sorted(unknown)}")
    if raw.get("version") != 1:
        raise StandardsError(f"{config_path}: version must be 1")

    paths = _path_list(raw.get("paths"), root, "paths", check_paths, allow_empty=False)
    deliverables = _section(raw.get("deliverables"), "deliverables", {"paths", "strict"})
    if "strict" in deliverables and deliverables["strict"] is not True:
        raise StandardsError("deliverables.strict cannot be turned off. Warnings fail on deliverables.")
    deliverable_paths = _path_list(deliverables.get("paths", []), root, "deliverables.paths", check_paths, allow_empty=True)

    slack = _section(raw.get("slack"), "slack", {"paths"})
    if "ban_semicolons" in slack:
        raise StandardsError("slack.ban_semicolons cannot be set. Slack drafts always ban semicolons.")
    slack_paths = _path_list(slack.get("paths", []), root, "slack.paths", check_paths, allow_empty=True)

    format_cfg = _section(raw.get("format"), "format", {"dates", "atomic_close", "lookups"})
    dates_enabled, dates_paths, require_weekday = _dates(format_cfg.get("dates"), root, check_paths)
    atomic_enabled, atomic_paths = _toggle_paths(
        format_cfg.get("atomic_close"), root, "format.atomic_close", check_paths, extra_keys=set()
    )
    lookups_enabled, lookup_paths, extra_lookups = _lookups(format_cfg.get("lookups"), root, check_paths)

    project = _section(raw.get("project"), "project", {"paths"})
    project_paths = _path_list(project.get("paths", []), root, "project.paths", check_paths, allow_empty=True)

    generated_cfg = _section(raw.get("generated"), "generated", {"enabled"})
    generated = _bool(generated_cfg.get("enabled", False), "generated.enabled")

    rules_path = _optional_file(raw.get("rules"), root, "rules", check_paths)
    corrections_path = _optional_file(raw.get("corrections"), root, "corrections", check_paths)

    extra_raw = _extra_banned(raw, root, check_paths)
    shared = read_rule_document(DATA / "banned.yaml")["rules"]
    shared_ids = {rule.get("id") for rule in shared}
    for rule in extra_raw:
        rule_id = rule.get("id") if isinstance(rule, dict) else None
        if rule_id in shared_ids:
            raise StandardsError(
                f"extra rule {rule_id} collides with a shared rule. Shared rules cannot be replaced."
            )
    compiled = compile_rules(shared + extra_raw, f"{DATA / 'banned.yaml'} + {config_path}")
    return Config(
        root=root,
        config_path=config_path,
        paths=paths,
        deliverable_paths=deliverable_paths,
        slack_paths=slack_paths,
        rules=compiled,
        banned_ids={rule["id"] for rule in compiled},
        rules_path=rules_path,
        corrections_path=corrections_path,
        dates_enabled=dates_enabled,
        dates_paths=dates_paths,
        require_weekday=require_weekday,
        atomic_enabled=atomic_enabled,
        atomic_paths=atomic_paths,
        lookups_enabled=lookups_enabled,
        lookup_paths=lookup_paths,
        extra_lookups=extra_lookups,
        project_paths=project_paths,
        generated=generated,
        raw=raw,
    )


def _extra_banned(raw: dict, root: Path, check_paths: bool) -> list[dict]:
    inline = raw.get("extra_banned", [])
    if not isinstance(inline, list):
        raise StandardsError("extra_banned must be a list")
    rules = list(inline)
    file_value = raw.get("extra_banned_file")
    if file_value is not None:
        path = _resolve(file_value, root, "extra_banned_file", check_paths)
        document = read_rule_document(path)
        rules.extend(document["rules"])
    for rule in rules:
        if not isinstance(rule, dict):
            raise StandardsError("extra_banned entries must be mappings")
    return rules


def _dates(section: object, root: Path, check_paths: bool) -> tuple[bool, list[Path], bool]:
    if section is None:
        return False, [], False
    data = _section(section, "format.dates", {"enabled", "paths", "require_weekday"})
    enabled = _bool(data.get("enabled", False), "format.dates.enabled")
    require_weekday = _bool(data.get("require_weekday", False), "format.dates.require_weekday")
    paths = _path_list(data.get("paths", []), root, "format.dates.paths", check_paths, allow_empty=not enabled)
    if enabled and not paths:
        raise StandardsError("format.dates.enabled needs at least one path")
    return enabled, paths, require_weekday


def _lookups(section: object, root: Path, check_paths: bool) -> tuple[bool, list[Path], tuple[str, ...]]:
    if section is None:
        return False, [], ()
    data = _section(section, "format.lookups", {"enabled", "paths", "extra_functions"})
    enabled = _bool(data.get("enabled", False), "format.lookups.enabled")
    paths = _path_list(data.get("paths", []), root, "format.lookups.paths", check_paths, allow_empty=not enabled)
    if enabled and not paths:
        raise StandardsError("format.lookups.enabled needs at least one path")
    extra = data.get("extra_functions", [])
    if not isinstance(extra, list) or not all(isinstance(item, str) for item in extra):
        raise StandardsError("format.lookups.extra_functions must be a list of names")
    for name in extra:
        if not IDENT_RE.fullmatch(name):
            raise StandardsError(f"format.lookups.extra_functions: {name!r} is not a function name")
    return enabled, paths, tuple(extra)


def _toggle_paths(
    section: object,
    root: Path,
    label: str,
    check_paths: bool,
    extra_keys: set[str],
) -> tuple[bool, list[Path]]:
    if section is None:
        return False, []
    data = _section(section, label, {"enabled", "paths"} | extra_keys)
    enabled = _bool(data.get("enabled", False), f"{label}.enabled")
    paths = _path_list(data.get("paths", []), root, f"{label}.paths", check_paths, allow_empty=not enabled)
    if enabled and not paths:
        raise StandardsError(f"{label}.enabled needs at least one path")
    return enabled, paths


def _section(value: object, label: str, allowed: set[str]) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise StandardsError(f"{label} must be a mapping")
    unknown = set(value) - allowed
    if unknown:
        raise StandardsError(f"{label}: unknown keys {sorted(unknown)}")
    return value


def _path_list(value: object, root: Path, label: str, check_paths: bool, *, allow_empty: bool) -> list[Path]:
    if value is None:
        value = []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise StandardsError(f"{label} must be a list of paths")
    if not value and not allow_empty:
        raise StandardsError(f"{label} needs at least one path")
    return [_resolve(item, root, f"{label}[{index}]", check_paths) for index, item in enumerate(value)]


def _optional_file(value: object, root: Path, label: str, check_paths: bool) -> Path | None:
    if value is None:
        return None
    return _resolve(value, root, label, check_paths)


def _resolve(value: object, root: Path, label: str, check_paths: bool) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise StandardsError(f"{label} must be a path")
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    if check_paths and not path.exists():
        raise StandardsError(f"{label} does not exist: {value}")
    return path


def _bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise StandardsError(f"{label} must be true or false")
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
