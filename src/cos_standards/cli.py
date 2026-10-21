"""Run the shared checks against one repo's config."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from cos_standards.check_corrections import check_file as check_corrections_file
from cos_standards.check_generated import check_mirrors
from cos_standards.check_rules import check_merged, load_ledger, merge_ledgers
from cos_standards.config import load_config
from cos_standards.errors import StandardsError
from cos_standards.lint_format import check_atomic_close, check_lookups, check_task_dates
from cos_standards.lint_project import lint_project_text
from cos_standards.lint_slack import lint_slack_text
from cos_standards.lint_writing import (
    TEXT_EXTS,
    Hit,
    apply_strict,
    count,
    format_hit,
    lint_text,
)

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".gz",
    ".ico",
    ".woff",
    ".woff2",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint a repo against the shared operating-model standards.")
    parser.add_argument("--config", help="cos.yaml or standards/local.yaml. Default: search both.")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        config = load_config(args.config, root)
        hits, problems = collect(config)
    except StandardsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for hit in sorted(hits, key=lambda item: (item[0], item[1], item[2], item[4])):
        print(format_hit(hit))
    for problem in problems:
        print(problem, end="" if problem.endswith("\n") else "\n")
    errors, warnings = count(hits)
    errors += len(problems)
    if hits or problems:
        print(f"{errors} error(s), {warnings} warning(s)", file=sys.stderr)
    return 1 if errors else 0


def collect(config) -> tuple[list[Hit], list[str]]:
    hits: list[Hit] = []
    problems: list[str] = []
    strict_files = set(expand_text(config.deliverable_paths)) | set(expand_text(config.slack_paths))
    writing_files: dict[Path, bool] = {}
    for path in expand_text(config.paths):
        writing_files[path] = path in strict_files
    for path in strict_files:
        writing_files[path] = True

    for path, strict in sorted(writing_files.items()):
        hits.extend(apply_strict(lint_text(_read(path), str(path), config.rules), strict))

    for path in expand_text(config.slack_paths):
        hits.extend(lint_slack_text(_read(path), str(path)))

    if config.dates_enabled:
        for path in expand_text(config.dates_paths):
            hits.extend(check_task_dates(_read(path), str(path), require_weekday=config.require_weekday))
    if config.atomic_enabled:
        for path in expand_text(config.atomic_paths):
            hits.extend(check_atomic_close(_read(path), str(path)))
    if config.lookups_enabled:
        for path in expand_lookup_files(config.lookup_paths):
            text = _read_maybe(path)
            if text is None:
                continue
            hits.extend(check_lookups(text, str(path), config.extra_lookups))

    for path in expand_text(config.project_paths):
        hits.extend(lint_project_text(_read(path), str(path)))

    rule_problems = check_merged(config.rules_path, config.root, config.banned_ids)
    problems.extend(_with_location(config.rules_path, rule_problems, fallback="rules.yaml"))

    if config.corrections_path is not None:
        local_rules = load_ledger(config.rules_path) if config.rules_path is not None else []
        rule_ids = {rule["id"] for rule in merge_ledgers(local_rules)}
        correction_problems = check_corrections_file(config.corrections_path, rule_ids=rule_ids)
        problems.extend(f"{config.corrections_path}: error: {problem}" for problem in correction_problems)

    if config.generated:
        problems.extend(check_mirrors(config.root))
    return hits, problems


def expand_text(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            for dirpath, dirnames, filenames in os.walk(path):
                dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS and not name.endswith(".egg-info")]
                for filename in sorted(filenames):
                    if Path(filename).suffix.lower() in TEXT_EXTS:
                        found.append(Path(dirpath) / filename)
        elif path.is_file():
            found.append(path)
    return sorted(set(found))


def expand_lookup_files(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_file():
            found.append(path)
            continue
        if not path.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS and not name.endswith(".egg-info")]
            for filename in sorted(filenames):
                candidate = Path(dirpath) / filename
                if candidate.suffix.lower() in BINARY_SUFFIXES:
                    continue
                found.append(candidate)
    return sorted(set(found))


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise StandardsError(f"{path}: {exc}") from exc


def _read_maybe(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise StandardsError(f"{path}: {exc}") from exc
    if len(data) > 1_000_000 or b"\0" in data[:1024]:
        return None
    return data.decode("utf-8", errors="replace")


def _with_location(path: Path | None, problems: list[str], *, fallback: str) -> list[str]:
    label = str(path) if path is not None else fallback
    return [f"{label}: error: {problem}" for problem in problems]


if __name__ == "__main__":
    sys.exit(main())
