from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cos_standards.check_comments import problems as comment_problems
from cos_standards.check_corrections import check_file as check_corrections_file
from cos_standards.check_generated import check_mirrors
from cos_standards.check_lookups import problems as lookup_problems
from cos_standards.check_outward import problems as outward_problems
from cos_standards.check_rules import check as check_rules
from cos_standards.check_rules import is_package_repo
from cos_standards.config import load_config
from cos_standards.errors import StandardsError
from cos_standards.lint_deliverables import collect as collect_files
from cos_standards.lint_format import problems as format_problems
from cos_standards.lint_shape import problems as shape_problems
from cos_standards.lint_writing import lint_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint a repo against the shared operating-model standards.")
    parser.add_argument("--config", help="cos.yaml or standards/local.yaml. Default: search both, then run with defaults.")
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
        print(f"{hit[0]}:{hit[1]}:{hit[2]}: {hit[3]}: [{hit[4]}] {hit[5]!r} {hit[6]}")
    for problem in problems:
        print(problem, end="" if problem.endswith("\n") else "\n")
    errors = len(hits) + len(problems)
    if hits or problems:
        print(f"{errors} error(s), 0 warning(s)", file=sys.stderr)
    return 1 if errors else 0


def collect(config) -> tuple[list, list[str]]:
    hits = []
    problems: list[str] = []
    for path in collect_files(config.root):
        hits.extend(_strict(lint_file(str(path), config.rules)))
    problems.extend(shape_problems(config.root, max_lines=config.slack_max_lines))
    problems.extend(
        format_problems(
            config.root,
            notion_paths=config.notion_paths,
            vendor_paths=config.vendor_paths,
            max_bullets=config.vendor_max_bullets,
            max_words=config.vendor_max_words,
        )
    )
    problems.extend(lookup_problems(config.root))
    problems.extend(comment_problems(config.root))
    problems.extend(
        outward_problems(
            {"folders": config.outward_folders, "terms": config.outward_terms},
            config.root,
        )
    )
    problems.extend(check_rules(config.root, config.rules_path))
    if config.corrections_path is not None:
        problems.extend(check_corrections_file(config.corrections_path))
    if is_package_repo(config.root):
        problems.extend(check_mirrors(config.root))
    return hits, problems


def _strict(hits: list) -> list:
    promoted = []
    for hit in hits:
        if hit[3] == "warn":
            promoted.append((hit[0], hit[1], hit[2], "error", hit[4], hit[5], hit[6]))
        else:
            promoted.append(hit)
    return promoted


if __name__ == "__main__":
    sys.exit(main())
