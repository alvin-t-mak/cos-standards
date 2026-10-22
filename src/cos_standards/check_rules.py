"""Fail if a marked rule is missing from the ledger, or the reverse.

A rule is an HTML comment whose body is `rule:` plus the id, in AGENTS.md,
docs/*.md, or standards/*.md. Generated files are skipped. Each ledger entry
needs a `check` id this package implements, or an `uncheckable` reason. A
local rule may instead set `check` to `job:` plus a job id that exists in
`.github/workflows/*.yml`. The shared ledger cannot.

In this package repo, every shared rule is marked. In a consuming repo, shared
rules do not need a local row. A local id that matches a shared id is rejected.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

from cos_standards.errors import StandardsError
from cos_standards.paths import package_repo

RULE_RE = re.compile(r"<!--\s*rule:\s*([a-z0-9-]+)\s*-->")
JOB_RE = re.compile(r"job:([A-Za-z_][A-Za-z0-9_-]*)\Z")
SKIP = {
    "docs/banned.md",
    "standards/banned.md",
    "docs/REPO_MAP.md",
    "standards/REPO_MAP.md",
}
DATA = Path(__file__).resolve().parent / "data"

# Check ids that a program in this package actually runs.
IMPLEMENTED = {
    "slack-line-cap",
    "decision-request-shape",
    "writing-lint",
    "banned-matches-generator",
    "model-verify",
    "corrections-encoded",
    "outward-names",
    "no-vlookup",
    "task-dates",
    "atomic-close",
    "slack-no-semicolon",
    "vendor-notes",
    "notion-day-labels",
}


def _load_rules(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise StandardsError(f"{path}: {exc}") from exc
    rules = data.get("rules") if isinstance(data, dict) else None
    if not isinstance(rules, list):
        raise StandardsError(f"{path} needs a rules list")
    return rules


def shared_rules() -> list[dict]:
    return _load_rules(DATA / "rules.yaml")


def marker_ids(root: Path | None = None) -> dict[str, list[str]]:
    root = root or package_repo()
    found: dict[str, list[str]] = {}
    files: list[Path] = []
    agents = root / "AGENTS.md"
    if agents.is_file():
        files.append(agents)
    for folder in ("docs", "standards"):
        base = root / folder
        if base.is_dir():
            files.extend(sorted(base.glob("*.md")))
    for path in files:
        rel = path.relative_to(root).as_posix()
        if rel in SKIP or not path.is_file():
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in RULE_RE.finditer(line):
                found.setdefault(match.group(1), []).append(f"{rel}:{i}")
    return found


def ledger(root: Path | None = None) -> list[dict]:
    """Shared rules plus local additions from standards/rules.yaml."""
    root = root or package_repo()
    shared = shared_rules()
    shared_ids = {rule.get("id") for rule in shared}
    local = _load_rules(root / "standards" / "rules.yaml")
    return shared + [rule for rule in local if rule.get("id") not in shared_ids]


def workflow_job_ids(root: Path) -> set[str]:
    """Job ids under `jobs` in `.github/workflows/*.yml`. Display names do not count."""
    folder = root / ".github" / "workflows"
    found: set[str] = set()
    if not folder.is_dir():
        return found
    for path in sorted(folder.glob("*.yml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            raise StandardsError(f"{path}: {exc}") from exc
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(jobs, dict):
            continue
        for key in jobs:
            if isinstance(key, str):
                found.add(key)
    return found


def _check_ref_problems(rid: str, check: object, *, local: bool, job_ids: set[str]) -> list[str]:
    if not isinstance(check, str) or not check.strip():
        return [f"{rid}: needs check or uncheckable"]
    text = check.strip()
    if text.startswith("job:"):
        if not local:
            return [f"{rid}: the shared ledger cannot use a job check"]
        match = JOB_RE.fullmatch(text)
        if not match:
            return [f"{rid}: check {text} must be job: plus a job id"]
        job_id = match.group(1)
        if job_id not in job_ids:
            return [f"{rid}: job {job_id} is not in .github/workflows"]
        return []
    if text not in IMPLEMENTED:
        return [f"{rid}: check {text} is not implemented"]
    return []


def problems(
    markers: dict[str, list[str]],
    rules: list[dict],
    *,
    job_ids: set[str] | None = None,
    local_ids: set[str] | None = None,
) -> list[str]:
    job_ids = set() if job_ids is None else job_ids
    local_ids = set() if local_ids is None else local_ids
    out = []
    seen = []
    for rule in rules:
        rid = rule.get("id")
        if not rid:
            out.append("ledger entry missing id")
            continue
        seen.append(rid)
        has_check = bool(rule.get("check"))
        has_reason = bool(rule.get("uncheckable"))
        if has_check and has_reason:
            out.append(f"{rid}: set check or uncheckable, not both")
        elif not has_check and not has_reason:
            out.append(f"{rid}: needs check or uncheckable")
        elif has_check:
            out.extend(_check_ref_problems(rid, rule["check"], local=rid in local_ids, job_ids=job_ids))
        if rid not in markers:
            out.append(f"{rid}: in the ledger but not marked in a doc")
    dupes = {rid for rid in seen if seen.count(rid) > 1}
    for rid in sorted(dupes):
        out.append(f"{rid}: duplicated in the ledger")
    for rid, places in sorted(markers.items()):
        if rid not in seen:
            out.append(f"{rid}: marked at {places[0]} but missing from the ledger")
        if len(places) > 1:
            out.append(f"{rid}: marked more than once ({', '.join(places)})")
    return out


def _collisions(local: list[dict], shared: list[dict]) -> list[str]:
    shared_ids = {rule.get("id") for rule in shared}
    out = []
    for rule in local:
        rid = rule.get("id")
        if rid and rid in shared_ids:
            out.append(f"{rid}: collides with a shared rule")
    return out


def consumer_problems(
    markers: dict[str, list[str]],
    local_rules: list[dict],
    shared: list[dict] | None = None,
    *,
    job_ids: set[str] | None = None,
) -> list[str]:
    shared = shared_rules() if shared is None else shared
    shared_ids = {rule.get("id") for rule in shared}
    out = _collisions(local_rules, shared)
    for rid, places in sorted(markers.items()):
        if rid in shared_ids and len(places) > 1:
            out.append(f"{rid}: marked more than once ({', '.join(places)})")
    local_markers = {rid: places for rid, places in markers.items() if rid not in shared_ids}
    filtered = [rule for rule in local_rules if rule.get("id") not in shared_ids]
    local_ids = {rule.get("id") for rule in filtered}
    out.extend(problems(local_markers, filtered, job_ids=job_ids, local_ids=local_ids))
    return out


def is_package_repo(root: Path) -> bool:
    return (root / "src" / "cos_standards" / "data" / "rules.yaml").is_file()


def check(root: Path, local_path: Path | None = None) -> list[str]:
    markers = marker_ids(root)
    shared = shared_rules()
    local = _load_rules(local_path) if local_path is not None else []
    jobs = workflow_job_ids(root)
    shared_ids = {rule.get("id") for rule in shared}
    if is_package_repo(root):
        filtered = [rule for rule in local if rule.get("id") not in shared_ids]
        local_ids = {rule.get("id") for rule in filtered}
        return _collisions(local, shared) + problems(
            markers, shared + filtered, job_ids=jobs, local_ids=local_ids
        )
    return consumer_problems(markers, local, shared, job_ids=jobs)


def main(argv: list[str] | None = None) -> int:
    root = Path(argv[0]) if argv else package_repo()
    try:
        found = check(root, root / "standards" / "rules.yaml")
    except StandardsError as exc:
        print(f"rule ledger failed: {exc}", file=sys.stderr)
        return 2
    if found:
        print(f"{len(found)} rule ledger problem(s)")
        for item in found:
            print(" ", item)
        return 1
    print("rule ledger ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
