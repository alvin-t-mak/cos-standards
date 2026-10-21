"""The repo lints itself, and the consumer contract stays in the README."""

import json
from pathlib import Path

from cos_standards.check_generated import check_mirrors
from cos_standards.cli import main
from cos_standards.verify_models import main as verify_main

ROOT = Path(__file__).resolve().parents[1]


def test_repo_lints_clean():
    assert main(["--root", str(ROOT)]) == 0


def test_generated_mirrors_match():
    assert check_mirrors(ROOT) == []


def test_verify_with_no_models_exits_clean(tmp_path: Path):
    code = verify_main(["--root", str(ROOT), "--receipt", str(tmp_path / "verify-receipt.json"), "--skip-recalc"])
    assert code == 0
    receipt = json.loads((tmp_path / "verify-receipt.json").read_text(encoding="utf-8"))
    assert receipt["ok"] is True
    assert receipt["models"] == []
    assert receipt["unlisted_scripts"] == []


def test_unlisted_build_script_fails(tmp_path: Path):
    (tmp_path / "build_hidden.py").write_text("print(1)\n", encoding="utf-8")
    receipt_path = tmp_path / "verify-receipt.json"
    code = verify_main(["--root", str(tmp_path), "--receipt", str(receipt_path), "--skip-recalc"])
    assert code == 1
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["unlisted_scripts"] == ["build_hidden.py"]


def test_readme_embeds_the_caller_and_schema():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in (
        "examples/standards.yml",
        "examples/cos.yaml",
        "examples/models.yaml",
        "examples/outward.yaml",
    ):
        snippet = (ROOT / name).read_text(encoding="utf-8").strip()
        assert snippet in readme, name
    assert "jobs:\n  lint:" in readme
    assert "jobs:\n  verify:" in readme or "  verify:" in readme
    assert 'pip install "cos-standards @ git+https://github.com/alvin-t-mak/cos-standards"' in readme
    for name in (
        "standards/banned.yaml",
        "standards/lint_shape.py",
        "standards/verify_models.py",
        "standards/check_outward.py",
        "standards/tests/slack/good-decision.md",
        "standards/README.md",
    ):
        assert f"`{name}`" in readme


def test_reusable_workflows_are_call_only():
    for name in ("lint.yml", "verify.yml"):
        text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "workflow_call:" in text
        assert "pull_request:" not in text
        assert "git+https://github.com/alvin-t-mak/cos-standards@" in text
    lint = (ROOT / ".github" / "workflows" / "lint.yml").read_text(encoding="utf-8")
    verify = (ROOT / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")
    assert "jobs:\n  lint:" in lint
    assert "name: lint" in lint
    assert "cos-lint" in lint
    assert "jobs:\n  verify:" in verify
    assert "name: verify" in verify
    assert "cos-verify" in verify
    assert "libreoffice-calc" in verify
    assert "verify-receipt" in verify


def test_public_tree_has_no_private_detail():
    banned = (
        "lightfield",
        "attio",
        "tryalma",
        "faction.ai",
        "alvin@",
        "veroa.ai",
        "hockeystack",
        "umpisa",
        "veroa",
    )
    skip = {".git", "_src", "__pycache__", ".pytest_cache", ".venv", "tests", "dist", "build"}
    leaks: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in skip or part.endswith(".egg-info") for part in path.parts):
            continue
        if path.suffix.lower() in {".png", ".pyc"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").casefold()
        for needle in banned:
            if needle in text:
                leaks.append(f"{needle} in {path.relative_to(ROOT)}")
    assert leaks == []
