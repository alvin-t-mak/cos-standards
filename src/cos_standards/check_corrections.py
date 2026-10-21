"""corrections.yaml schema.

A correction sits at the narrowest scope that would have prevented it.
Broad scopes are rejected. Recurrence of 2 or more must be promoted:
status encoded, and promoted_to a rule id in the merged ledger.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

from cos_standards.errors import StandardsError

BROAD_SCOPES = {"all", "global", "everything", "general", "repo", "any", "anywhere", "everywhere", "*"}
SCOPE_RE = re.compile(r"^[a-z0-9][a-z0-9._/-]{0,80}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}$")
ENTRY_KEYS = {"id", "date", "scope", "correction", "recurrence", "status", "promoted_to"}
STATUSES = {"open", "encoded"}


def load_corrections(path: Path) -> list[dict]:
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
    extra = set(data) - {"version", "corrections"}
    if extra:
        raise StandardsError(f"{path}: unknown keys {sorted(extra)}")
    if data.get("version") != 1:
        raise StandardsError(f"{path}: version must be 1")
    corrections = data.get("corrections")
    if not isinstance(corrections, list):
        raise StandardsError(f"{path}: corrections must be a list")
    return corrections


def check_correction_list(corrections: list[dict], *, rule_ids: set[str]) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    seen_body: set[tuple[str, str]] = set()
    if not isinstance(corrections, list):
        return ["corrections must be a list"]
    for index, item in enumerate(corrections, start=1):
        label = f"correction {index}"
        if not isinstance(item, dict):
            problems.append(f"{label}: expected a mapping")
            continue
        extra = set(item) - ENTRY_KEYS
        if extra:
            problems.append(f"{label}: unknown keys {sorted(extra)}")
            continue
        missing = {"id", "date", "scope", "correction"} - set(item)
        if missing:
            problems.append(f"{label}: missing {sorted(missing)}")
            continue
        rule_id = item["id"]
        label = str(rule_id)
        if not isinstance(rule_id, str) or not ID_RE.fullmatch(rule_id):
            problems.append(f"{label}: id must be a lowercase slug")
            continue
        if rule_id in seen:
            problems.append(f"{rule_id}: duplicate id")
        seen.add(rule_id)
        if _as_date(item["date"]) is None:
            problems.append(f"{rule_id}: date must be YYYY-MM-DD")
        scope = item["scope"]
        if not isinstance(scope, str) or scope.casefold() in BROAD_SCOPES or not SCOPE_RE.fullmatch(scope):
            problems.append(
                f"{rule_id}: scope must be the narrowest surface (for example slack, memo, or a path). "
                f"{sorted(BROAD_SCOPES)} are rejected."
            )
        text = item["correction"]
        if not isinstance(text, str) or not text.strip():
            problems.append(f"{rule_id}: correction must be a non-empty string")
        elif isinstance(scope, str):
            body = (scope, " ".join(text.split()).casefold())
            if body in seen_body:
                problems.append(f"{rule_id}: duplicate correction at the same scope")
            seen_body.add(body)
        recurrence = item.get("recurrence", 1)
        if isinstance(recurrence, bool) or not isinstance(recurrence, int) or recurrence < 1:
            problems.append(f"{rule_id}: recurrence must be an integer >= 1")
            continue
        status = item.get("status", "open")
        if status not in STATUSES:
            problems.append(f"{rule_id}: status must be open or encoded")
            continue
        promoted = item.get("promoted_to")
        if recurrence >= 2 and status != "encoded":
            problems.append(f"{rule_id}: recurrence {recurrence} must be promoted (status: encoded)")
        if recurrence >= 2 and not promoted:
            problems.append(f"{rule_id}: recurrence {recurrence} needs promoted_to, a rule id with an enforcement")
        if status == "encoded" and not promoted:
            problems.append(f"{rule_id}: encoded corrections need promoted_to")
        if promoted is not None:
            if not isinstance(promoted, str) or promoted not in rule_ids:
                problems.append(f"{rule_id}: promoted_to {promoted!r} is not a rule in the merged ledger")
    return problems


def check_file(path: Path, *, rule_ids: set[str]) -> list[str]:
    return check_correction_list(load_corrections(path), rule_ids=rule_ids)


def _as_date(value: object) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def main(argv: list[str] | None = None) -> int:
    from cos_standards.check_rules import merge_ledgers
    from cos_standards.config import load_config

    parser = argparse.ArgumentParser(description="Check corrections.yaml against the schema.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--config", default=None)
    parser.add_argument("corrections", nargs="?")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        config = load_config(args.config, root)
        path = Path(args.corrections).resolve() if args.corrections else config.corrections_path
        if path is None:
            raise StandardsError("no corrections file. Set corrections: in the config or pass a path.")
        if not path.is_file():
            raise StandardsError(f"corrections file not found: {path}")
        local: list[dict] = []
        if config.rules_path is not None:
            from cos_standards.check_rules import load_ledger

            local = load_ledger(config.rules_path)
        rule_ids = {rule["id"] for rule in merge_ledgers(local)}
        problems = check_file(path, rule_ids=rule_ids)
    except StandardsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"{path}: error: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
