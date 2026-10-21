"""Slack shape, format checks, config merge, and the ledgers."""

from pathlib import Path

import pytest

from cos_standards.check_corrections import check_correction_list
from cos_standards.check_generated import diff_generated
from cos_standards.check_rules import check_merged, check_rule_list, merge_ledgers
from cos_standards.config import load_config
from cos_standards.errors import StandardsError
from cos_standards.lint_deliverables import lint_deliverable_text
from cos_standards.lint_format import check_atomic_close, check_lookups, check_task_dates
from cos_standards.lint_project import lint_project_text
from cos_standards.lint_slack import lint_slack_text
from cos_standards.lint_writing import load_rules

ROOT = Path(__file__).resolve().parents[1]
RULES = load_rules(None)

DECISION = """Need a call on the Jan offsite by Fri. The venue hold expires then.
1. Austin, in person, $85K (recommended)
2. Virtual, $10K
3. Push to Q1, $0 now, goals slip to March
Why 1: the offsite has to produce the goals, and the last two virtual ones ended without a plan.
If no answer by Fri, I go with 1.
Assumes the travel line survives the budget review. If it is cut, I pick 2.
"""

PROJECT = """# Close pack

## Goal

Ship the close pack.

## Done when

- The memo is in the repo.

## Scope

In: the memo. Out: sending it.

## Criteria

- Answer in the first line.

## Criteria added

- 2026-10-21: Keep the memo under one page.
"""


def ids(hits):
    return {hit[4] for hit in hits}


def test_decision_shape_passes():
    assert lint_slack_text(DECISION, "slack.md") == []


def test_decision_shape_failures():
    missing = DECISION.replace(" (recommended)", "").replace("Why 1: the offsite has to produce the goals, and the last two virtual ones ended without a plan.\n", "").replace("If no answer by Fri, I go with 1.\n", "")
    found = ids(lint_slack_text(missing, "slack.md"))
    assert {"slack-recommended", "slack-why", "slack-default-deadline"} <= found


def test_why_must_be_one_line():
    text = DECISION.replace(
        "Why 1: the offsite has to produce the goals, and the last two virtual ones ended without a plan.\n",
        "Why 1: the offsite has to produce the goals,\nand the last two virtual ones ended without a plan.\n",
    )
    assert "slack-why" in ids(lint_slack_text(text, "slack.md"))


def test_default_without_deadline_fails():
    text = DECISION.replace("If no answer by Fri, I go with 1.", "Default: option 1")
    assert "slack-default-deadline" in ids(lint_slack_text(text, "slack.md"))


def test_option_count_and_order():
    text = "1. One (recommended)\n3. Three\nWhy 1: because it is ready.\nIf no answer by Fri, I go with 1.\n"
    assert "slack-options" in ids(lint_slack_text(text, "slack.md"))


def test_status_note_skips_shape_but_bans_semicolons():
    assert lint_slack_text("Q4 budget is $180K over. I will send a fix by Thursday.", "s.md") == []
    assert "slack-semicolon" in ids(lint_slack_text("Q4 is over; I will send a fix.", "s.md"))
    assert lint_slack_text("Run `a; b` and send the file.", "s.md") == []


def test_parenthetical_options_count():
    text = DECISION.replace("1.", "1)").replace("2.", "2)").replace("3.", "3)")
    assert lint_slack_text(text, "slack.md") == []


def test_task_dates():
    good = "- [ ] Ship the note \U0001f4c5 2026-10-21\n- [ ] Aim for \u23f3 2026-10-22 (Thu)\n"
    assert check_task_dates(good, "tasks.md") == []
    assert ids(check_task_dates("- [ ] Ship 2026-10-21\n", "tasks.md")) == {"task-date-syntax"}
    assert ids(check_task_dates("- [ ] Ship \U0001f4c5 2026-02-31\n", "tasks.md")) == {"task-date-syntax"}
    assert ids(check_task_dates("- [ ] Ship \U0001f4c5 2026-10-21 (Mon)\n", "tasks.md")) == {"task-date-weekday"}
    both = "- [ ] Ship \U0001f4c5 2026-10-21 \u23f3 2026-10-22\n"
    assert "task-date-syntax" in ids(check_task_dates(both, "tasks.md"))
    assert ids(check_task_dates("- [ ] Ship \U0001f4c5 2026-10-21\n", "tasks.md", require_weekday=True)) == {
        "task-date-weekday"
    }


def test_atomic_close():
    closed = "- [x] Ship \U0001f4c5 2026-10-21 | receipt: merged\n"
    assert check_atomic_close(closed, "tasks.md") == []
    assert "atomic-receipt" in ids(check_atomic_close("- [x] Ship \U0001f4c5 2026-10-21\n", "tasks.md"))
    assert "atomic-partial" in ids(check_atomic_close("- [~] Ship the note\n", "tasks.md"))
    open_receipt = "- [ ] Ship \u23f3 2026-10-22 | receipt: early\n"
    assert "atomic-receipt-on-open" in ids(check_atomic_close(open_receipt, "tasks.md"))
    parent = (
        "- [x] Parent \U0001f4c5 2026-10-21 | receipt: merged\n"
        "  - [ ] Child \u23f3 2026-10-22\n"
    )
    assert "atomic-open-child" in ids(check_atomic_close(parent, "tasks.md"))
    done = (
        "- [x] Parent \U0001f4c5 2026-10-21 | receipt: merged\n"
        "  - [x] Child \U0001f4c5 2026-10-21 | receipt: step ok\n"
    )
    assert check_atomic_close(done, "tasks.md") == []


def test_lookups_keep_the_core_three():
    assert check_lookups("=INDEX(C:C, MATCH(A2, B:B, 0))", "m.py") == []
    assert "lookup-banned" in ids(check_lookups("=XLOOKUP(A2, B:B, C:C)", "m.py"))
    assert "lookup-banned" in ids(check_lookups("VLOOKUP is in a fence\n```\n=VLOOKUP(A1,B:C,2,FALSE)\n```", "m.md"))
    hits = check_lookups("=ZZLOOKUP(A1)", "m.py", extra=("ZZLOOKUP",))
    assert "ZZLOOKUP" in hits[0][5]
    # An extra list that omits the core names does not drop them.
    assert "lookup-banned" in ids(check_lookups("=HLOOKUP(A1,B:C,2,FALSE)", "m.py", extra=("ZZLOOKUP",)))


def test_project_contract():
    assert lint_project_text(PROJECT, "project.md") == []
    empty_log = PROJECT.replace("- 2026-10-21: Keep the memo under one page.\n", "")
    assert lint_project_text(empty_log, "project.md") == []
    two = PROJECT.replace("Ship the close pack.", "Ship the close pack. Then stop.")
    assert "project-goal" in ids(lint_project_text(two, "project.md"))
    missing = PROJECT.replace("## Criteria\n\n- Answer in the first line.\n\n", "")
    assert "project-heading" in ids(lint_project_text(missing, "project.md"))
    bad_log = PROJECT.replace("- 2026-10-21: Keep the memo under one page.", "- sometime later")
    assert "project-criteria-added" in ids(lint_project_text(bad_log, "project.md"))


def test_deliverables_promote_warnings():
    text = "We can leverage the existing model."
    assert ids(lint_deliverable_text(text, "d.md", RULES)) == {"leverage"}
    assert all(hit[3] == "error" for hit in lint_deliverable_text(text, "d.md", RULES))


def test_config_rejects_weakening(tmp_path: Path):
    note = tmp_path / "notes.md"
    note.write_text("Hello.\n", encoding="utf-8")
    base = "version: 1\npaths:\n  - notes.md\n"

    def load(extra: str):
        path = tmp_path / "cos.yaml"
        path.write_text(base + extra, encoding="utf-8")
        return load_config(str(path), tmp_path)

    with pytest.raises(StandardsError, match="cannot disable"):
        load("disable:\n  - em-dash\n")
    with pytest.raises(StandardsError, match="cannot disable"):
        load("format:\n  dates:\n    exemptions: [task-date-syntax]\n    enabled: false\n")
    with pytest.raises(StandardsError, match="strict cannot be turned off"):
        load("deliverables:\n  paths: []\n  strict: false\n")
    with pytest.raises(StandardsError, match="unknown keys"):
        load("slack:\n  paths: []\n  ban_semicolons: false\n")
    with pytest.raises(StandardsError, match="collides"):
        load(
            "extra_banned:\n"
            "  - id: em-dash\n"
            "    category: punctuation\n"
            "    type: literal\n"
            "    pattern: x\n"
            "    severity: warn\n"
            "    reason: weaken\n"
        )


def test_config_adds_a_rule(tmp_path: Path):
    note = tmp_path / "notes.md"
    note.write_text("The zz-local-term slipped in.\n", encoding="utf-8")
    (tmp_path / "cos.yaml").write_text(
        "version: 1\npaths:\n  - notes.md\nextra_banned:\n"
        "  - id: repo-specific-term\n    category: phrase\n    type: literal\n"
        "    pattern: zz-local-term\n    severity: error\n    reason: local term\n",
        encoding="utf-8",
    )
    config = load_config(None, tmp_path)
    assert "em-dash" in config.banned_ids
    assert "repo-specific-term" in config.banned_ids
    from cos_standards.lint_writing import lint_text

    found = ids(lint_text(note.read_text(encoding="utf-8"), "notes.md", config.rules))
    assert "repo-specific-term" in found


def test_ledger_and_corrections(tmp_path: Path):
    assert check_merged(ROOT / "standards" / "rules.yaml", ROOT, {rule["id"] for rule in RULES}) == []
    with pytest.raises(StandardsError, match="collides"):
        merge_ledgers(
            [
                {
                    "id": "writing-banned-list",
                    "statement": "replace",
                    "enforcement": {"kind": "script", "ref": "cos_standards.lint_writing:lint_text"},
                }
            ]
        )
    problems = check_rule_list(
        [
            {
                "id": "hand-review",
                "statement": "A person reads it.",
                "enforcement": {"kind": "manual", "ref": "alvin"},
            }
        ],
        tmp_path,
        {"em-dash"},
    )
    assert any("not enforcement" in problem for problem in problems)
    problems = check_rule_list(
        [
            {
                "id": "missing-lint",
                "statement": "Points at a rule that is not in the list.",
                "enforcement": {"kind": "lint", "ref": "not-a-rule"},
            }
        ],
        tmp_path,
        {"em-dash"},
    )
    assert any("not a banned rule" in problem for problem in problems)

    rule_ids = {"writing-banned-list"}
    assert check_correction_list([], rule_ids=rule_ids) == []
    good = [
        {
            "id": "em-dash-slip",
            "date": "2026-10-21",
            "scope": "slack",
            "correction": "A draft used an em dash.",
            "recurrence": 2,
            "status": "encoded",
            "promoted_to": "writing-banned-list",
        }
    ]
    assert check_correction_list(good, rule_ids=rule_ids) == []
    broad = [dict(good[0], scope="global")]
    assert any("scope" in problem for problem in check_correction_list(broad, rule_ids=rule_ids))
    unpromoted = [dict(good[0], status="open", promoted_to=None)]
    found = check_correction_list(unpromoted, rule_ids=rule_ids)
    assert any("promoted" in problem for problem in found)


def test_diff_generated_helper():
    assert diff_generated("banned.md", "a\n", "a\n") == ""
    diff = diff_generated("banned.md", "a\n", "b\n")
    assert "banned.md (committed)" in diff
    assert "banned.md (generated)" in diff
