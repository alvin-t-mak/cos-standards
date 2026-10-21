"""Deterministic writing linter.

Rules come from banned.yaml (needs PyYAML) or banned.json (stdlib only), in this
package's data directory unless --rules is given. Matching is case-insensitive.
Curly apostrophes and quotes are normalized to straight ones before matching.

Skipped text: fenced code blocks (``` or ~~~), inline `code` spans, and any line
containing the marker "lint: ignore". A file with "lint: ignore-file" in its
first 5 lines is skipped entirely (used by banned.md, which quotes banned text).

Exit codes: 0 clean (or warnings only), 1 at least one error, 2 bad config/usage.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from cos_standards.errors import StandardsError

DATA = Path(__file__).resolve().parent / "data"
IGNORE_MARKER = "lint: ignore"
IGNORE_FILE_MARKER = "lint: ignore-file"  # must appear in the first 5 lines
FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE_RE = re.compile(r"(`+)(.+?)\1")
# Curly quotes become straight ones so "it's" matches either glyph.
# Every replacement is one character, so columns stay correct.
NORMALIZE = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"'})
TEXT_EXTS = {".md", ".markdown", ".txt"}

# A hit is (name, line, column, severity, rule id, match, reason).
Hit = tuple[str, int, int, str, str, str, str]


def read_rule_document(path: Path) -> dict:
    try:
        if path.suffix.lower() in {".yaml", ".yml"}:
            try:
                import yaml
            except ImportError as exc:
                raise StandardsError("PyYAML is not installed; use a banned.json rules file") from exc
            with path.open(encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
        else:
            with path.open(encoding="utf-8") as handle:
                data = json.load(handle)
    except StandardsError:
        raise
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise StandardsError(f"{path}: {exc}") from exc
    except Exception as exc:
        # PyYAML raises yaml.YAMLError, which is not a subclass of ValueError.
        if exc.__class__.__name__ == "YAMLError":
            raise StandardsError(f"{path}: {exc}") from exc
        raise
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise StandardsError(f"{path}: expected a mapping with a rules list")
    return data


def load_rules(path: str | None) -> list[dict]:
    """Compile rules from an explicit file, or from the packaged banned list."""
    if path:
        candidate = Path(path)
        if not candidate.is_file():
            raise StandardsError(f"rules file not found: {path}")
        data = read_rule_document(candidate)
        return compile_rules(data["rules"], str(candidate))

    for name in ("banned.yaml", "banned.json"):
        candidate = DATA / name
        if not candidate.is_file():
            continue
        try:
            data = read_rule_document(candidate)
        except StandardsError:
            if name.endswith((".yaml", ".yml")):
                continue
            raise
        return compile_rules(data["rules"], str(candidate))
    raise StandardsError("no rules file found (banned.yaml or banned.json)")


def compile_rules(raw: list[dict], src: str) -> list[dict]:
    rules: list[dict] = []
    problems: list[str] = []
    seen: set[str] = set()
    for rule in raw:
        if not isinstance(rule, dict):
            problems.append("rule is not a mapping")
            continue
        missing = {"id", "pattern", "type", "severity", "reason"} - rule.keys()
        if missing:
            problems.append(f"{rule.get('id', '?')}: missing {sorted(missing)}")
            continue
        rule_id = rule["id"]
        if rule_id in seen:
            problems.append(f"{rule_id}: duplicate id")
            continue
        seen.add(rule_id)
        if rule["severity"] not in ("error", "warn"):
            problems.append(f"{rule_id}: severity must be error or warn")
            continue
        if rule["type"] == "literal":
            literal = str(rule["pattern"])
            pattern = re.escape(literal)
            if literal[:1].isalnum():
                pattern = r"\b" + pattern
            if literal[-1:].isalnum():
                pattern = pattern + r"\b"
        elif rule["type"] == "regex":
            pattern = str(rule["pattern"])
        else:
            problems.append(f"{rule_id}: type must be literal or regex")
            continue
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
            allow = re.compile(rule["allow"], re.IGNORECASE) if rule.get("allow") else None
        except re.error as exc:
            problems.append(f"{rule_id}: bad regex: {exc}")
            continue
        rules.append({**rule, "rx": compiled, "allow_rx": allow})
    if problems:
        raise StandardsError(f"invalid rules in {src}:\n  " + "\n  ".join(problems))
    return rules


def blank_inline_code(line: str) -> str:
    return INLINE_CODE_RE.sub(lambda match: " " * len(match.group(0)), line)


def prepare_lines(text: str) -> list[tuple[int, str, str]] | None:
    """Return (line number, raw line, match line) or None when the file is skipped.

    The match line has curly quotes folded and inline code blanked. It is the
    same length as the raw line, so a match column still points at the raw text.
    """
    if any(IGNORE_FILE_MARKER in line for line in text.splitlines()[:5]):
        return None
    visible: list[tuple[int, str, str]] = []
    in_fence = False
    for lineno, raw in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence or IGNORE_MARKER in raw:
            continue
        visible.append((lineno, raw, blank_inline_code(raw.translate(NORMALIZE))))
    return visible


def lint_text(text: str, name: str, rules: list[dict]) -> list[Hit]:
    prepared = prepare_lines(text)
    if prepared is None:
        return []
    hits: list[Hit] = []
    for lineno, raw, line in prepared:
        for rule in rules:
            allowed = [span.span() for span in rule["allow_rx"].finditer(line)] if rule["allow_rx"] else []
            for match in rule["rx"].finditer(line):
                if any(start <= match.start() and match.end() <= end for start, end in allowed):
                    continue
                hits.append(
                    (
                        name,
                        lineno,
                        match.start() + 1,
                        rule["severity"],
                        rule["id"],
                        raw[match.start() : match.end()],
                        rule["reason"],
                    )
                )
    return hits


def apply_strict(hits: list[Hit], strict: bool) -> list[Hit]:
    if not strict:
        return hits
    upgraded: list[Hit] = []
    for name, lineno, col, severity, rule_id, match, reason in hits:
        if severity == "warn":
            severity = "error"
        upgraded.append((name, lineno, col, severity, rule_id, match, reason))
    return upgraded


def iter_files(paths: list[str]):
    for raw_path in paths:
        if os.path.isdir(raw_path):
            for root, dirnames, files in os.walk(raw_path):
                dirnames[:] = [name for name in dirnames if name not in {".git", "__pycache__", ".pytest_cache"}]
                for filename in sorted(files):
                    if os.path.splitext(filename)[1].lower() in TEXT_EXTS:
                        yield os.path.join(root, filename)
        else:
            yield raw_path


def format_hit(hit: Hit) -> str:
    name, lineno, col, severity, rule_id, match, reason = hit
    return f"{name}:{lineno}:{col}: {severity}: [{rule_id}] {match!r} {reason}"


def count(hits: list[Hit]) -> tuple[int, int]:
    errors = sum(1 for hit in hits if hit[3] == "error")
    warnings = sum(1 for hit in hits if hit[3] == "warn")
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint writing against banned.yaml / banned.json.")
    parser.add_argument("paths", nargs="*", help="files or directories; '-' or nothing for stdin")
    parser.add_argument("--rules", help="path to banned.yaml or banned.json")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--errors-only", action="store_true", help="hide warnings")
    parser.add_argument("--export-json", action="store_true", help="write banned.json from banned.yaml and exit")
    args = parser.parse_args(argv)

    try:
        if args.export_json:
            source = Path(args.rules) if args.rules else DATA / "banned.yaml"
            data = read_rule_document(source)
            compile_rules(data["rules"], str(source))
            destination = source.with_name("banned.json") if source.suffix.lower() in {".yaml", ".yml"} else source
            if source.suffix.lower() in {".yaml", ".yml"}:
                destination = source.parent / "banned.json"
            destination.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
            print(f"wrote {destination} ({len(data['rules'])} rules)")
            return 0

        rules = load_rules(args.rules)
        hits: list[Hit] = []
        if not args.paths or args.paths == ["-"]:
            hits.extend(lint_text(sys.stdin.read(), "<stdin>", rules))
        else:
            for path in iter_files(args.paths):
                try:
                    text = Path(path).read_text(encoding="utf-8", errors="replace")
                except OSError as exc:
                    print(f"error: {exc}", file=sys.stderr)
                    return 2
                hits.extend(lint_text(text, path, rules))
        hits = apply_strict(hits, args.strict)
    except StandardsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    errors, warnings = _emit(hits, errors_only=args.errors_only)
    return 1 if errors else 0


def _emit(hits: list[Hit], *, errors_only: bool = False) -> tuple[int, int]:
    errors, warnings = count(hits)
    shown = 0
    for hit in sorted(hits, key=lambda item: (item[0], item[1], item[2], item[4])):
        if hit[3] == "warn" and errors_only:
            continue
        print(format_hit(hit))
        shown += 1
    if shown:
        print(f"{errors} error(s), {warnings} warning(s)", file=sys.stderr)
    return errors, warnings


if __name__ == "__main__":
    sys.exit(main())
