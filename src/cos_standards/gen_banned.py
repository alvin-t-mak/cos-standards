# lint: ignore-file
"""Render banned.json and docs/banned.md from banned.yaml."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from cos_standards.errors import StandardsError
from cos_standards.lint_writing import DATA, compile_rules, read_rule_document

CATEGORIES = [
    (
        "punctuation",
        "Punctuation (dashes)",
        'Em dashes and double-hyphen stand-ins are banned. En dashes are allowed everywhere, '
        'spaced or not ("Hey Sam – thanks", "2024–2026"), and so is a spaced single hyphen. '
        "Code and CLI flags in backticks are skipped.",
    ),
    (
        "phrase",
        "(a) Hard-ban words and phrases",
        "Almost never legitimate in a terse business Slack message. Severity: error.",
    ),
    (
        "structure",
        "(b) Hard-ban structural patterns",
        "Sentence shapes, sycophantic openers, filler closers, and chatbot artifacts. Severity: error.",
    ),
    (
        "warn",
        "(c) Warn only",
        "Sometimes legitimate. Reported, and they do not fail the lint unless the run is strict. "
        "Deliverables run strict, so a warning there fails the check.",
    ),
]


def render_json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True) + "\n"


def render_md(data: dict) -> str:
    rules = data["rules"]

    def show(value: str) -> str:
        return "".join(char if ord(char) < 128 else f"U+{ord(char):04X}" for char in value)

    counts = Counter((rule["category"], rule["severity"]) for rule in rules)
    out: list[str] = []
    out.append(
        """<!-- lint: ignore-file (this file quotes banned text on purpose) -->
# Banned list for written deliverables

Machine-readable source: `src/cos_standards/data/banned.yaml` (mirrored to `banned.json`).
Checker: `cos-lint`. A consuming repo may add rules. It cannot delete or weaken these.

## How the rules work

- All matching is case-insensitive. Curly apostrophes are treated as straight ones.
- `literal` rules match the exact text, with word boundaries added at letter or digit edges.
- `regex` rules are Python `re` patterns.
- Optional `allow` regex on a rule: a hit that sits entirely inside an `allow` match is skipped.
- `error` fails the lint (exit code 1). `warn` is reported only. Strict mode, which deliverables use, makes warnings fail.
- Skipped: fenced code blocks, inline code in backticks, and any line containing `lint: ignore`.
- Matching is per line, so a phrase split across a hard line wrap is missed. Slack messages rarely wrap, so this is accepted.
- `lint: ignore` and `lint: ignore-file` exist so a standards file can quote a banned phrase. They are not a config exemption. Local config has no exemption key. This file uses `lint: ignore-file` because it quotes banned text.

## Counts

| Category | Severity | Rules |
| --- | --- | --- |
"""
    )
    for key, title, _blurb in CATEGORIES:
        for severity in ("error", "warn"):
            if counts[(key, severity)]:
                out.append(f"| {title} | {severity} | {counts[(key, severity)]} |\n")
    out.append(f"| Total | | {len(rules)} |\n\n")
    out.append(
        "Not covered by regex (check by eye): rule-of-three lists for rhythm, bold inline-header "
        "bullet lists in short messages, emoji bullets, Title Case Headings in a Slack message, "
        'vague attributions ("experts say", "industry reports"), and generic praise that could apply to any topic.\n\n'
    )
    for key, title, blurb in CATEGORIES:
        out.append(f"## {title}\n\n{blurb}\n\n")
        for rule in rules:
            if rule["category"] != key:
                continue
            severity = "" if key in ("phrase", "structure") else f" ({rule['severity']})"
            out.append(f"- **{rule['id']}**{severity}: `{show(str(rule['pattern']))}` ({rule['type']}). {show(str(rule['reason']))}\n")
        out.append("\n")
    out.append(
        """## Sources

- Wikipedia, "Signs of AI writing" (AI vocabulary, negative parallelisms, superficial analysis, promotional tone, chatbot phrasing, placeholder text, citation artifacts): https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
- Matsui, K. (2024). "Delving into PubMed Records: Some Terms in Medical Writing Have Drastically Changed after the Arrival of ChatGPT." medRxiv: https://www.medrxiv.org/content/10.1101/2024.05.14.24307373v2.full
- Kobak et al., excess-vocabulary analysis of biomedical abstracts: https://github.com/berenslab/chatgpt-excess-words
- Juzek and Ward (2024). "Why Does ChatGPT 'Delve' So Much? Exploring the Sources of Lexical Overrepresentation in Large Language Models." arXiv: https://arxiv.org/html/2412.11385
- Embryo, "A list of words that AI over-uses": https://embryo.com/blog/list-words-ai-overuses/

Approach (deterministic lint rules for agent and human writing) inspired by Lauren (@poteto)'s agent setup.
"""
    )
    return "".join(out)


def load_banned(path: Path | None = None) -> dict:
    source = path or (DATA / "banned.yaml")
    data = read_rule_document(source)
    compile_rules(data["rules"], str(source))
    return data


def markdown_path(root: Path) -> Path:
    return root / "docs" / "banned.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate banned.json and docs/banned.md from banned.yaml.")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        data = load_banned()
    except StandardsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    json_path = DATA / "banned.json"
    md_path = markdown_path(root)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(render_json(data), encoding="utf-8")
    md_path.write_text(render_md(data), encoding="utf-8")
    print(f"wrote {json_path} and {md_path} ({len(data['rules'])} rules)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
