from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "lightfield-automations.md"
CHECKLIST = ROOT / "standards" / "lightfield-automation-checklist.yaml"

REQUIRED_HEADINGS = [
    "## Trigger",
    "## Purpose",
    "## May write",
    "## Never write",
    "## Sources",
    "## Skip rules",
    "## Idempotency",
    "## Read-back",
    "## Stop and report",
    "## Output",
    "## Owner",
    "## Kill switch",
    "## Instructions",
]

NEVER_WRITE = [
    "computed dollar fields",
    "rollups",
    "$amount",
    "Recruiterflow id fields",
    "Gfteams",
    "Flexpressai",
    "Veroa",
]

POINTER = "Lightfield automation work follows `docs/lightfield-automations.md`."


def _section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = lines.index(heading)
    end = start + 1
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    return "\n".join(lines[start + 1 : end])


def test_lightfield_checklist_matches_the_standard():
    data = yaml.safe_load(CHECKLIST.read_text(encoding="utf-8"))
    assert list(data) == ["required_headings", "never_write"]
    assert data["required_headings"] == REQUIRED_HEADINGS
    assert data["never_write"] == NEVER_WRITE
    text = DOC.read_text(encoding="utf-8")
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    assert headings == data["required_headings"]
    never = _section(text, "## Never write")
    for item in data["never_write"]:
        assert item in never
    assert "veroa-vault" in text
    assert "lightfield/automations/<slug>.md" in text
    assert "pull request" in text
    assert "verbatim" in text
    assert "stopped:" in _section(text, "## Stop and report")
    assert "Pause the automation" in _section(text, "## Kill switch")
    for name in ("AGENTS.md", "CLAUDE.md", ".cursor/rules/no-comments.mdc"):
        assert POINTER in (ROOT / name).read_text(encoding="utf-8")
