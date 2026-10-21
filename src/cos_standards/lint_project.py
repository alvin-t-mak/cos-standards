"""project.md contract.

Required sections, in order: Goal, Done when, Scope, Criteria, Criteria added.
Goal is one sentence. Criteria is non-empty (taste criteria up front).
Criteria added is a log of lines `YYYY-MM-DD: ...`, or empty.
"""

from __future__ import annotations

import datetime as dt
import re

from cos_standards.lint_writing import Hit

REQUIRED = ("Goal", "Done when", "Scope", "Criteria", "Criteria added")
ENTRY_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}): \S")
BULLET_RE = re.compile(r"^(?:[-*] |\d+[.)] )")


def _hit(name: str, lineno: int, rule_id: str, match: str, reason: str) -> Hit:
    return (name, lineno, 1, "error", rule_id, match, reason)


def lint_project_text(text: str, name: str) -> list[Hit]:
    hits: list[Hit] = []
    lines = text.splitlines()
    first = next((index for index, line in enumerate(lines) if line.strip()), None)
    if first is None or not lines[first].startswith("# "):
        hits.append(_hit(name, 1, "project-heading", "", "project.md starts with an h1."))

    order, bodies, headings = _sections(lines)
    duplicates = [heading for heading in order if order.count(heading) > 1]
    for heading in sorted(set(duplicates)):
        hits.append(_hit(name, headings[heading], "project-heading", heading, "Duplicate section."))

    for heading in REQUIRED:
        if heading not in bodies:
            hits.append(_hit(name, 1, "project-heading", heading, f"Missing section '## {heading}'."))

    present = [heading for heading in order if heading in REQUIRED]
    if all(heading in bodies for heading in REQUIRED) and present != list(REQUIRED):
        hits.append(
            _hit(
                name,
                1,
                "project-heading",
                " > ".join(present),
                "Sections go in this order: " + ", ".join(REQUIRED) + ".",
            )
        )

    if "Goal" in bodies:
        goal_lines = _content(bodies["Goal"])
        goal = goal_lines[0] if len(goal_lines) == 1 else ""
        if len(goal_lines) != 1 or len(re.findall(r"[.!?]", goal)) != 1:
            hits.append(_hit(name, headings.get("Goal", 1), "project-goal", goal, "Goal is one sentence."))

    if "Done when" in bodies:
        done = _content(bodies["Done when"])
        if not any(BULLET_RE.match(line) for line in done):
            hits.append(
                _hit(
                    name,
                    headings.get("Done when", 1),
                    "project-done",
                    "",
                    "Done when is a list of checkable lines.",
                )
            )

    if "Scope" in bodies and not _content(bodies["Scope"]):
        hits.append(_hit(name, headings.get("Scope", 1), "project-scope", "", "Scope says what is in and what is out."))

    if "Criteria" in bodies and not any(line.startswith("- ") or line.startswith("* ") for line in _content(bodies["Criteria"])):
        hits.append(
            _hit(
                name,
                headings.get("Criteria", 1),
                "project-criteria",
                "",
                "Criteria lists the taste bar before the work starts. At least one bullet.",
            )
        )

    if "Criteria added" in bodies:
        for offset, line in enumerate(bodies["Criteria added"].splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            match = ENTRY_RE.match(stripped)
            if not match:
                hits.append(
                    _hit(
                        name,
                        headings.get("Criteria added", 1) + offset,
                        "project-criteria-added",
                        stripped[:80],
                        "A Criteria added line is '- YYYY-MM-DD: <criterion>'.",
                    )
                )
                continue
            try:
                dt.date.fromisoformat(match.group(1))
            except ValueError:
                hits.append(
                    _hit(
                        name,
                        headings.get("Criteria added", 1) + offset,
                        "project-criteria-added",
                        match.group(1),
                        "The Criteria added date is not a real calendar date.",
                    )
                )
    return hits


def _sections(lines: list[str]) -> tuple[list[str], dict[str, str], dict[str, int]]:
    order: list[str] = []
    buckets: dict[str, list[str]] = {}
    headings: dict[str, int] = {}
    current: str | None = None
    for lineno, line in enumerate(lines, start=1):
        if line.startswith("## "):
            current = line[3:].strip()
            order.append(current)
            headings.setdefault(current, lineno)
            buckets.setdefault(current, [])
            continue
        if current is not None:
            buckets[current].append(line)
    bodies = {key: "\n".join(value) for key, value in buckets.items()}
    return order, bodies, headings


def _content(body: str) -> list[str]:
    return [line.strip() for line in body.splitlines() if line.strip()]
