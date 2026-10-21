"""Every rule in the merged ledger has an enforcement that resolves.

Shared rules ship in this package. A repo's rules.yaml is appended.
A local rule cannot reuse a shared id.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from cos_standards.errors import StandardsError
from cos_standards.lint_writing import DATA

ID_RE_SRC = r"^[a-z0-9][a-z0-9-]{0,60}$"
RULE_KEYS = {"id", "statement", "enforcement"}
ENFORCEMENT_KEYS = {"kind", "ref"}
KINDS = {"lint", "script", "test", "ci"}
FORBIDDEN_KINDS = {"manual", "human", "none", "review", "waived", "off", "exempt"}


def load_ledger(path: Path) -> list[dict]:
    try:
        import yaml
    except ImportError as exc:
        raise StandardsError("PyYAML is not installed") from exc
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise StandardsError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise StandardsError(f"{path}: expected a mapping")
    extra = set(data) - {"version", "rules"}
    if extra:
        raise StandardsError(f"{path}: unknown keys {sorted(extra)}")
    if data.get("version") != 1:
        raise StandardsError(f"{path}: version must be 1")
    rules = data.get("rules")
    if not isinstance(rules, list):
        raise StandardsError(f"{path}: rules must be a list")
    for index, rule in enumerate(rules, start=1):
        _validate_rule_shape(rule, f"{path} rule {index}")
    return rules


def merge_ledgers(local_rules: list[dict]) -> list[dict]:
    shared = load_ledger(DATA / "rules.yaml")
    shared_ids = {rule["id"] for rule in shared}
    for rule in local_rules:
        if rule["id"] in shared_ids:
            raise StandardsError(
                f"local rule {rule['id']} collides with a shared rule. Shared rules cannot be replaced."
            )
    return shared + local_rules


def check_rule_list(rules: list[dict], root: Path, banned_ids: set[str]) -> list[str]:
    """Return one problem string per rule whose enforcement does not resolve."""
    problems: list[str] = []
    seen: set[str] = set()
    for rule in rules:
        rule_id = str(rule.get("id", "?"))
        if rule_id in seen:
            problems.append(f"{rule_id}: duplicate id")
        seen.add(rule_id)
        enforcement = rule.get("enforcement")
        if not isinstance(enforcement, dict):
            problems.append(f"{rule_id}: missing enforcement")
            continue
        message = resolve_enforcement(enforcement, root=root, banned_ids=banned_ids)
        if message:
            problems.append(f"{rule_id}: {message}")
    return problems


def resolve_enforcement(enforcement: dict, *, root: Path, banned_ids: set[str]) -> str | None:
    kind = enforcement.get("kind")
    ref = enforcement.get("ref")
    if not isinstance(kind, str) or not isinstance(ref, str) or not ref.strip():
        return "enforcement needs a kind and a ref"
    if kind in FORBIDDEN_KINDS:
        return f"kind {kind!r} is not enforcement. Human review does not count."
    if kind not in KINDS:
        return f"unknown enforcement kind {kind!r}"
    if kind == "lint":
        if ref not in banned_ids:
            return f"lint ref {ref!r} is not a banned rule"
        return None
    if kind == "script":
        if ":" not in ref or "/" in ref.split(":", 1)[0]:
            return "script ref must be module:function"
        module_name, func_name = ref.rsplit(":", 1)
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            return f"cannot import {module_name}: {exc}"
        function = getattr(module, func_name, None)
        if not callable(function):
            return f"{ref} is not callable"
        return None
    if kind == "test":
        file_part, _, test_name = ref.partition("::")
        path = root / file_part
        if not path.is_file():
            return f"test file not found: {file_part}"
        if test_name and test_name not in path.read_text(encoding="utf-8"):
            return f"test {test_name} not found in {file_part}"
        return None
    path = root / ref
    if not path.is_file():
        return f"workflow not found: {ref}"
    text = path.read_text(encoding="utf-8")
    if "uses:" not in text and "run:" not in text:
        return f"workflow has no steps: {ref}"
    return None


def check_merged(local_path: Path | None, root: Path, banned_ids: set[str]) -> list[str]:
    local: list[dict] = []
    if local_path is not None:
        local = load_ledger(local_path)
    rules = merge_ledgers(local)
    return check_rule_list(rules, root, banned_ids)


def _validate_rule_shape(rule: object, label: str) -> None:
    import re

    if not isinstance(rule, dict):
        raise StandardsError(f"{label}: expected a mapping")
    extra = set(rule) - RULE_KEYS
    if extra:
        raise StandardsError(f"{label}: unknown keys {sorted(extra)}")
    missing = RULE_KEYS - set(rule)
    if missing:
        raise StandardsError(f"{label}: missing {sorted(missing)}")
    if not isinstance(rule["id"], str) or not re.fullmatch(ID_RE_SRC, rule["id"]):
        raise StandardsError(f"{label}: id must be a lowercase slug")
    if not isinstance(rule["statement"], str) or not rule["statement"].strip():
        raise StandardsError(f"{label}: statement must be a non-empty string")
    enforcement = rule["enforcement"]
    if not isinstance(enforcement, dict):
        raise StandardsError(f"{label}: enforcement must be a mapping")
    extra = set(enforcement) - ENFORCEMENT_KEYS
    if extra:
        raise StandardsError(f"{label}: unknown enforcement keys {sorted(extra)}")
    if not isinstance(enforcement.get("kind"), str) or not isinstance(enforcement.get("ref"), str):
        raise StandardsError(f"{label}: enforcement needs string kind and ref")


def main(argv: list[str] | None = None) -> int:
    from cos_standards.config import load_config

    parser = argparse.ArgumentParser(description="Check that every ledger rule has an enforcement.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--config", default=None)
    parser.add_argument("rules", nargs="?", help="local rules.yaml (additions). Shared rules are always included.")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        config = load_config(args.config, root)
        local = Path(args.rules).resolve() if args.rules else config.rules_path
        if args.rules and not local.is_file():
            raise StandardsError(f"rules file not found: {args.rules}")
        problems = check_merged(local, root, config.banned_ids)
    except StandardsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"error: [{problem.split(':', 1)[0]}] {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
