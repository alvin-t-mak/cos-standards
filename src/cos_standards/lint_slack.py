"""Slack draft shape.

A draft that uses a numbered list, a recommended mark, a Why line, or a default
line has to satisfy the whole decision shape: 2 to 4 numbered options, exactly
one of them marked (recommended), one Why line, and one default-deadline line.

Semicolons are banned in every Slack draft. Inline code and fenced blocks are
skipped, same as the writing linter.
"""

from __future__ import annotations

import re

from cos_standards.lint_writing import Hit, prepare_lines

OPTION_RE = re.compile(r"^\s*(\d+)[.)]\s+\S")
RECOMMENDED_RE = re.compile(r"\(recommended\)", re.IGNORECASE)
WHY_RE = re.compile(r"^\s*Why\b[^:\n]{0,40}:\s*\S", re.IGNORECASE)
ASSUMES_RE = re.compile(r"^\s*Assumes\b", re.IGNORECASE)
DEFAULT_RE = re.compile(r"^\s*(?:If no answer by\b|Default\s*:).+\S", re.IGNORECASE)
DEADLINE_CUE_RE = re.compile(
    r"\b(?:by|before|eod|cob|today|tomorrow|mon|tue|wed|thu|fri|sat|sun|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2})\b",
    re.IGNORECASE,
)
SEMICOLON_RE = re.compile(r";")


def _hit(name: str, lineno: int, col: int, rule_id: str, match: str, reason: str) -> Hit:
    return (name, lineno, col, "error", rule_id, match, reason)


def lint_semicolons(text: str, name: str) -> list[Hit]:
    prepared = prepare_lines(text)
    if prepared is None:
        return []
    hits: list[Hit] = []
    for lineno, raw, line in prepared:
        for match in SEMICOLON_RE.finditer(line):
            hits.append(
                _hit(
                    name,
                    lineno,
                    match.start() + 1,
                    "slack-semicolon",
                    raw[match.start() : match.end()],
                    "Slack drafts do not use semicolons. Use a period or a new line.",
                )
            )
    return hits


def lint_decision_shape(text: str, name: str) -> list[Hit]:
    prepared = prepare_lines(text)
    if prepared is None:
        return []
    lines = [(lineno, raw, blank) for lineno, raw, blank in prepared]
    blanks = [blank for _, _, blank in lines]
    if not _needs_shape(blanks):
        return []

    hits: list[Hit] = []
    option_rows = [(index, OPTION_RE.match(blank)) for index, blank in enumerate(blanks)]
    options = [(index, match) for index, match in option_rows if match]
    numbers = [int(match.group(1)) for _, match in options]
    expected = list(range(1, len(numbers) + 1))
    anchor = lines[options[0][0]][0] if options else (lines[0][0] if lines else 1)

    if numbers != expected or not (2 <= len(numbers) <= 4):
        hits.append(
            _hit(
                name,
                anchor,
                1,
                "slack-options",
                str(numbers or "none"),
                "A Slack decision has 2 to 4 numbered options, starting at 1 with no gaps.",
            )
        )

    recommended_options = [index for index, _ in options if RECOMMENDED_RE.search(blanks[index])]
    recommended_other = [
        index for index, blank in enumerate(blanks) if RECOMMENDED_RE.search(blank) and index not in {i for i, _ in options}
    ]
    recommended_count = len(recommended_options) + len(recommended_other)
    if recommended_count != 1 or recommended_other:
        where = lines[(recommended_options or recommended_other or [0])[0]][0]
        hits.append(
            _hit(
                name,
                where,
                1,
                "slack-recommended",
                "(recommended)",
                "Mark exactly one numbered option with (recommended).",
            )
        )

    why_indexes = [index for index, blank in enumerate(blanks) if WHY_RE.match(blank)]
    if len(why_indexes) != 1:
        where = lines[why_indexes[0]][0] if why_indexes else anchor
        hits.append(
            _hit(
                name,
                where,
                1,
                "slack-why",
                "Why" if why_indexes else "",
                "Include one Why line, and only one.",
            )
        )
    else:
        why_index = why_indexes[0]
        follower = _next_content(blanks, why_index)
        if follower is not None and not _is_shape_line(blanks[follower]):
            hits.append(
                _hit(
                    name,
                    lines[follower][0],
                    1,
                    "slack-why",
                    blanks[follower].strip()[:80],
                    "The Why line is one line. Do not continue it on the next line.",
                )
            )

    default_indexes = [
        index for index, blank in enumerate(blanks) if DEFAULT_RE.match(blank) and DEADLINE_CUE_RE.search(blank)
    ]
    default_weak = [
        index
        for index, blank in enumerate(blanks)
        if DEFAULT_RE.match(blank) and not DEADLINE_CUE_RE.search(blank)
    ]
    if len(default_indexes) != 1 or default_weak:
        where = lines[(default_indexes or default_weak or [0])[0]][0] if lines else 1
        hits.append(
            _hit(
                name,
                where,
                1,
                "slack-default-deadline",
                "default",
                "Include one default-deadline line, such as 'If no answer by Fri, I go with 1.'",
            )
        )
    return hits


def lint_slack_text(text: str, name: str) -> list[Hit]:
    return lint_semicolons(text, name) + lint_decision_shape(text, name)


def _needs_shape(lines: list[str]) -> bool:
    for line in lines:
        if OPTION_RE.match(line) or RECOMMENDED_RE.search(line) or WHY_RE.match(line) or DEFAULT_RE.match(line):
            return True
    return False


def _is_shape_line(line: str) -> bool:
    return bool(OPTION_RE.match(line) or WHY_RE.match(line) or ASSUMES_RE.match(line) or DEFAULT_RE.match(line))


def _next_content(lines: list[str], index: int) -> int | None:
    for follower in range(index + 1, len(lines)):
        if lines[follower].strip():
            return follower
    return None
