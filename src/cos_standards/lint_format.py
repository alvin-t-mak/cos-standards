"""Configurable formatting checks.

The syntax is fixed. A repo chooses the paths, and may add lookup names.
It cannot rename the date markers or drop VLOOKUP, HLOOKUP, or XLOOKUP.
"""

from __future__ import annotations

import datetime as dt
import re

from cos_standards.lint_writing import FENCE_RE, Hit

HARD = "📅"
SOFT = "⏳"
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
CORE_LOOKUPS = ("VLOOKUP", "HLOOKUP", "XLOOKUP")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
BOX_RE = re.compile(r"^(\s*)[-*] \[([^\]]*)\] (.+)$")
MARKER_RE = re.compile(
    rf"({re.escape(HARD)}|{re.escape(SOFT)})\s+(\d{{4}}-\d{{2}}-\d{{2}})(?:\s+\((Mon|Tue|Wed|Thu|Fri|Sat|Sun)\))?"
)
ISO_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
RECEIPT_RE = re.compile(
    rf"(?:{re.escape(HARD)}|{re.escape(SOFT)})\s+\d{{4}}-\d{{2}}-\d{{2}}"
    r"(?:\s+\((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\))?\s+\|\s+\S"
)


def _hit(name: str, lineno: int, rule_id: str, match: str, reason: str) -> Hit:
    return (name, lineno, 1, "error", rule_id, match, reason)


def _visible(text: str) -> list[tuple[int, str]]:
    """Drop fenced examples so a doc can show the syntax."""
    rows: list[tuple[int, str]] = []
    in_fence = False
    for lineno, raw in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        rows.append((lineno, raw))
    return rows


def _tasks(text: str) -> list[tuple[int, int, str, str]]:
    """Return (lineno, indent, box, body) for checkbox lines outside fences."""
    found: list[tuple[int, int, str, str]] = []
    for lineno, raw in _visible(text):
        match = BOX_RE.match(raw)
        if not match:
            continue
        indent = len(match.group(1).replace("\t", "  "))
        found.append((lineno, indent, match.group(2), match.group(3)))
    return found


def check_task_dates(text: str, name: str, require_weekday: bool = False) -> list[Hit]:
    hits: list[Hit] = []
    for lineno, _indent, box, body in _tasks(text):
        if box not in {" ", "x", "X"}:
            continue
        markers = list(MARKER_RE.finditer(body))
        if len(markers) != 1:
            hits.append(
                _hit(
                    name,
                    lineno,
                    "task-date-syntax",
                    body.strip()[:80],
                    f"A task date uses one {HARD} (hard) or one {SOFT} (soft), then YYYY-MM-DD.",
                )
            )
            continue
        marker = markers[0]
        iso = marker.group(2)
        weekday = marker.group(3)
        try:
            parsed = dt.date.fromisoformat(iso)
        except ValueError:
            hits.append(_hit(name, lineno, "task-date-syntax", iso, "The task date is not a real calendar date."))
            continue
        date_span = marker.span(2)
        bare = [match.group(0) for match in ISO_RE.finditer(body) if match.span() != date_span]
        if bare:
            hits.append(
                _hit(
                    name,
                    lineno,
                    "task-date-syntax",
                    bare[0],
                    f"Put the date after {HARD} or {SOFT}. A bare ISO date is not a task date.",
                )
            )
        trailing_weekday = re.match(r"\s+\(([A-Za-z]{3})\)", body[marker.end() :])
        if trailing_weekday:
            hits.append(
                _hit(
                    name,
                    lineno,
                    "task-date-weekday",
                    trailing_weekday.group(1),
                    "Weekday abbreviations are Mon, Tue, Wed, Thu, Fri, Sat, Sun.",
                )
            )
        elif weekday and WEEKDAYS[parsed.weekday()] != weekday:
            hits.append(
                _hit(
                    name,
                    lineno,
                    "task-date-weekday",
                    weekday,
                    f"{iso} is a {WEEKDAYS[parsed.weekday()]}, not {weekday}.",
                )
            )
        elif require_weekday and not weekday:
            hits.append(
                _hit(
                    name,
                    lineno,
                    "task-date-weekday",
                    iso,
                    "Add the weekday in parentheses, as in 2026-10-21 (Wed).",
                )
            )
    return hits


def check_atomic_close(text: str, name: str) -> list[Hit]:
    hits: list[Hit] = []
    tasks = _tasks(text)
    for index, (lineno, indent, box, body) in enumerate(tasks):
        if box not in {" ", "x", "X"}:
            hits.append(
                _hit(
                    name,
                    lineno,
                    "atomic-partial",
                    f"[{box}]",
                    "A task is open [ ] or closed [x]. Partial boxes are not a close.",
                )
            )
            continue
        closed = box in {"x", "X"}
        has_receipt = RECEIPT_RE.search(body) is not None
        if closed and not has_receipt:
            hits.append(
                _hit(
                    name,
                    lineno,
                    "atomic-receipt",
                    body.strip()[:80],
                    f"A closed task has one date ({HARD} or {SOFT}) and a receipt after |.",
                )
            )
        if not closed and has_receipt:
            hits.append(
                _hit(
                    name,
                    lineno,
                    "atomic-receipt-on-open",
                    body.strip()[:80],
                    "An open task does not carry a receipt. Close it, or remove the receipt.",
                )
            )
        if not closed:
            continue
        for child_line, child_indent, child_box, _child_body in tasks[index + 1 :]:
            if child_indent <= indent:
                break
            if child_box == " ":
                hits.append(
                    _hit(
                        name,
                        lineno,
                        "atomic-open-child",
                        f"line {child_line}",
                        "A closed task has no open child under it. Close the child or leave the parent open.",
                    )
                )
                break
    return hits


def check_lookups(text: str, name: str, extra: tuple[str, ...] | list[str] = ()) -> list[Hit]:
    names = _lookup_names(extra)
    pattern = re.compile(r"\b(" + "|".join(re.escape(item) for item in names) + r")\b", re.IGNORECASE)
    hits: list[Hit] = []
    # Lookups are banned in the file, including fenced formulas. A formula is not an example.
    for lineno, raw in enumerate(text.splitlines(), 1):
        for match in pattern.finditer(raw):
            hits.append(
                _hit(
                    name,
                    lineno,
                    "lookup-banned",
                    match.group(0),
                    f"{match.group(0)} is banned. Use a direct key match. VLOOKUP, HLOOKUP, and XLOOKUP cannot be removed.",
                )
            )
    return hits


def _lookup_names(extra: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    names = list(CORE_LOOKUPS)
    seen = {item.casefold() for item in names}
    for item in extra:
        if not isinstance(item, str) or not IDENT_RE.match(item):
            continue
        if item.casefold() in seen:
            continue
        seen.add(item.casefold())
        names.append(item)
    return tuple(names)
