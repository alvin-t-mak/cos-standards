import json
from pathlib import Path

import pytest

from cos_standards.check_pr_body import (
    REQUIRED,
    body_from_event,
    headings,
    main,
    paths_from_compare,
    problems,
)
from cos_standards.errors import StandardsError

ROOT = Path(__file__).resolve().parents[1]
BODY = "\n".join([
    "## Why",
    "",
    "The checker needed a source list.",
    "",
    "## Scope",
    "",
    "Code files only.",
    "",
    "## Blast radius",
    "",
    "Callers of cos-lint.",
    "",
    "## Verification",
    "",
    "pytest passed.",
    "",
])


def test_code_change_needs_the_four_headings(tmp_path: Path):
    found = problems("shipped it", ["src/app.py"], tmp_path)
    assert len(found) == 1
    assert "src/app.py" in found[0]
    assert "Why" in found[0]
    assert "Scope" in found[0]
    assert "Blast radius" in found[0]
    assert "Verification" in found[0]


def test_full_body_passes(tmp_path: Path):
    assert problems(BODY, ["src/app.py", "docs/principles.md"], tmp_path) == []


def test_docs_only_change_passes_without_headings(tmp_path: Path):
    assert problems("no headings", ["docs/principles.md", "README.md"], tmp_path) == []


def test_case_spacing_and_closing_hashes_pass(tmp_path: Path):
    body = "\n".join([
        "## why ##",
        "## SCOPE",
        "## Blast   radius",
        "# Verification",
        "",
    ])
    assert problems(body, ["q.sql"], tmp_path) == []


def test_fenced_headings_do_not_count(tmp_path: Path):
    fenced = "```\n## Why\n## Scope\n## Blast radius\n## Verification\n```\n"
    found = problems(fenced, ["a.py"], tmp_path)
    assert len(found) == 1
    assert headings(fenced) == set()


def test_longer_heading_does_not_count(tmp_path: Path):
    body = BODY.replace("## Why\n", "## Why this changed\n")
    found = problems(body, ["a.py"], tmp_path)
    assert len(found) == 1
    assert "Why" in found[0]
    assert "Scope" not in found[0].split("needs PR headings: ", 1)[1]


def test_rename_from_code_counts(tmp_path: Path):
    paths = paths_from_compare({
        "files": [{"filename": "docs/a.md", "previous_filename": "src/a.py", "status": "renamed"}],
    })
    found = problems("nope", paths, tmp_path)
    assert len(found) == 1
    assert "src/a.py" in found[0]


def test_compare_cap_fails():
    data = {"files": [{"filename": f"notes/f{i}.md"} for i in range(300)]}
    with pytest.raises(StandardsError, match="300"):
        paths_from_compare(data)


def test_compare_error_message_fails():
    with pytest.raises(StandardsError, match="Not Found"):
        paths_from_compare({"message": "Not Found"})


def test_empty_compare_has_no_paths():
    assert paths_from_compare({"status": "identical"}) == []


def test_cli_accepts_event_and_paths(tmp_path: Path):
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"body": BODY}}), encoding="utf-8")
    paths = tmp_path / "paths.txt"
    paths.write_text("src/app.py\ndocs/a.md\n", encoding="utf-8")
    assert main(["--root", str(tmp_path), "--event", str(event), "--paths-file", str(paths)]) == 0


def test_cli_fails_a_code_change_without_headings(tmp_path: Path):
    body = tmp_path / "body.md"
    body.write_text("shipped it\n", encoding="utf-8")
    compare = tmp_path / "compare.json"
    compare.write_text(json.dumps({"files": [{"filename": "src/app.py"}]}), encoding="utf-8")
    assert main(["--root", str(tmp_path), "--body-file", str(body), "--compare-file", str(compare)]) == 1


def test_cli_requires_a_body_and_a_path_list(tmp_path: Path):
    assert main(["--root", str(tmp_path)]) == 2


def test_null_body_is_empty(tmp_path: Path):
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"body": None}}), encoding="utf-8")
    assert body_from_event(event) == ""


def test_coding_doc_names_the_headings_and_lightfield():
    text = (ROOT / "docs" / "coding.md").read_text(encoding="utf-8")
    for name in REQUIRED:
        assert name in text
    assert "Lightfield automation code step" in text
    principles = (ROOT / "docs" / "principles.md").read_text(encoding="utf-8")
    assert "coding.md" in principles
    assert "Dropped because" not in principles
    for name in ("AGENTS.md", "CLAUDE.md", ".cursor/rules/no-comments.mdc"):
        notes = (ROOT / name).read_text(encoding="utf-8")
        assert "standards/code-scope.yaml" in notes
        assert "docs/coding.md" in notes
