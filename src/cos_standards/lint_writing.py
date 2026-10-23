from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from cos_standards.errors import StandardsError

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DATA = Path(HERE)
IGNORE_MARKER = "lint: ignore"
IGNORE_FILE_MARKER = "lint: ignore-file"
IGNORE_FILE_SCAN_LINES = 5
FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE_RE = re.compile(r"(`+)(.+?)\1")
NORMALIZE = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"'})
TEXT_EXTS = {".md", ".markdown", ".txt"}
CODE_EXTS = {".py", ".html", ".htm"}
DASH_IDS = {"em-dash", "horizontal-bar", "double-hyphen-dash"}

Hit = tuple[str, int, int, str, str, str, str]


def read_rule_document(path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise StandardsError("PyYAML is not installed") from exc
    try:
        data = yaml.safe_load(open(path, encoding="utf-8").read())
    except OSError as exc:
        raise StandardsError(f"{path}: {exc}") from exc
    except Exception as exc:
        raise StandardsError(f"{path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise StandardsError(f"{path}: expected a rules list")
    return data


def load_rules(path: str | None) -> list[dict]:
    candidates = [path] if path else [os.path.join(HERE, "banned.yaml"), os.path.join(HERE, "banned.json")]
    for cand in candidates:
        if not cand or not os.path.exists(cand):
            continue
        if cand.endswith((".yaml", ".yml")):
            try:
                import yaml
            except ImportError:
                if path:
                    raise StandardsError("PyYAML not installed; use --rules banned.json")
                continue
            with open(cand, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
            with open(cand, encoding="utf-8") as f:
                data = json.load(f)
        if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
            raise StandardsError(f"{cand}: expected a rules list")
        return compile_rules(data["rules"], cand)
    raise StandardsError("no rules file found (banned.yaml or banned.json)")


def compile_rules(raw: list[dict], src: str) -> list[dict]:
    rules, problems = [], []
    for r in raw:
        if not isinstance(r, dict):
            problems.append(f"rule is not a mapping: {r!r}")
            continue
        missing = {"id", "pattern", "type", "severity", "reason"} - r.keys()
        if missing:
            problems.append(f"{r.get('id', '?')}: missing {sorted(missing)}")
            continue
        if r["severity"] not in ("error", "warn"):
            problems.append(f"{r['id']}: severity must be error or warn")
            continue
        if r["type"] == "literal":
            lit = r["pattern"]
            pat = re.escape(lit)
            if lit[:1].isalnum():
                pat = r"\b" + pat
            if lit[-1:].isalnum():
                pat = pat + r"\b"
        elif r["type"] == "regex":
            pat = r["pattern"]
        else:
            problems.append(f"{r['id']}: type must be literal or regex")
            continue
        try:
            rx = re.compile(pat, re.IGNORECASE)
            allow = re.compile(r["allow"], re.IGNORECASE) if r.get("allow") else None
        except re.error as e:
            problems.append(f"{r['id']}: bad regex: {e}")
            continue
        rules.append({**r, "rx": rx, "allow_rx": allow})
    if problems:
        raise StandardsError(f"invalid rules in {src}:\n  " + "\n  ".join(problems))
    return rules


def blank_inline_code(line: str) -> str:
    return INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line)


def lint_text(text: str, name: str, rules: list[dict]) -> list[tuple]:
    hits = []
    if any(IGNORE_FILE_MARKER in ln for ln in text.splitlines()[:IGNORE_FILE_SCAN_LINES]):
        return hits
    in_fence = False
    for lineno, raw in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence or IGNORE_MARKER in raw:
            continue
        line = blank_inline_code(raw.translate(NORMALIZE))
        for r in rules:
            allowed = [a.span() for a in r["allow_rx"].finditer(line)] if r["allow_rx"] else []
            for m in r["rx"].finditer(line):
                if any(a0 <= m.start() and m.end() <= a1 for a0, a1 in allowed):
                    continue
                hits.append((name, lineno, m.start() + 1, r["severity"], r["id"], raw[m.start():m.end()], r["reason"]))
    return hits


def dash_rules(rules: list[dict]) -> list[dict]:
    return [r for r in rules if r["id"] in DASH_IDS]


def python_string_pieces(source: str):
    import io
    import tokenize

    readline = io.StringIO(source).readline
    try:
        tokens = tokenize.generate_tokens(readline)
    except tokenize.TokenizeError:
        return
    for tok in tokens:
        if tok.type == tokenize.STRING:
            try:
                import ast
                val = ast.literal_eval(tok.string)
            except (SyntaxError, ValueError):
                continue
            if isinstance(val, str):
                yield tok.start[0], val
        elif tok.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
            yield tok.start[0], tok.string


def lint_python(source: str, name: str, rules: list[dict]) -> list[tuple]:
    if any(IGNORE_FILE_MARKER in ln for ln in source.splitlines()[:IGNORE_FILE_SCAN_LINES]):
        return []
    source_lines = source.splitlines()
    hits = []
    for lineno, text in python_string_pieces(source):
        if 1 <= lineno <= len(source_lines) and IGNORE_MARKER in source_lines[lineno - 1]:
            continue
        for hit in lint_text(text, name, rules):
            hits.append((hit[0], lineno, hit[2], hit[3], hit[4], hit[5], hit[6]))
    return hits


def lint_file(path: str, rules: list[dict]) -> list[tuple]:
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    ext = os.path.splitext(path)[1].lower()
    if ext == ".py":
        return lint_python(text, path, rules)
    if ext in {".html", ".htm"}:
        return lint_text(text, path, dash_rules(rules))
    return lint_text(text, path, rules)


def iter_files(paths: list[str]):
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for fn in sorted(files):
                    if os.path.splitext(fn)[1].lower() in TEXT_EXTS:
                        yield os.path.join(root, fn)
        else:
            yield p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lint writing against banned.yaml / banned.json.")
    ap.add_argument("paths", nargs="*", help="files or directories; '-' or nothing for stdin")
    ap.add_argument("--rules", help="path to banned.yaml or banned.json")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--errors-only", action="store_true", help="hide warnings")
    ap.add_argument("--export-json", action="store_true", help="write banned.json from banned.yaml and exit")
    args = ap.parse_args(argv)

    try:
        if args.export_json:
            import yaml
            src = args.rules or os.path.join(HERE, "banned.yaml")
            with open(src, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            compile_rules(data["rules"], src)
            out = os.path.join(os.path.dirname(os.path.abspath(src)), "banned.json")
            with open(out, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=True)
                f.write("\n")
            print(f"wrote {out} ({len(data['rules'])} rules)")
            return 0

        rules = load_rules(args.rules)
    except StandardsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    hits = []
    if not args.paths or args.paths == ["-"]:
        hits += lint_text(sys.stdin.read(), "<stdin>", rules)
    else:
        for path in iter_files(args.paths):
            try:
                hits += lint_file(path, rules)
            except OSError as e:
                print(f"error: {e}", file=sys.stderr)
                return 2

    errors = warns = 0
    hits.sort(key=lambda h: (h[0], h[1], h[2]))
    for name, ln, col, sev, rid, match, reason in hits:
        if sev == "warn" and args.strict:
            sev = "error"
        if sev == "error":
            errors += 1
        else:
            warns += 1
            if args.errors_only:
                continue
        print(f"{name}:{ln}:{col}: {sev}: [{rid}] {match!r} {reason}")
    if hits:
        print(f"{errors} error(s), {warns} warning(s)", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
