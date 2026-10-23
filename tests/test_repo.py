import json
from pathlib import Path

from cos_standards.check_generated import check_mirrors
from cos_standards.cli import main
from cos_standards.lint_deliverables import collect
from cos_standards.verify_models import main as verify_main

ROOT = Path(__file__).resolve().parents[1]


def test_repo_lints_clean():
    assert main(["--root", str(ROOT)]) == 0


def test_bad_config_exits_2(tmp_path: Path):
    (tmp_path / "cos.yaml").write_text("version: 1\nskip: true\n", encoding="utf-8")
    assert main(["--root", str(tmp_path)]) == 2


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


def test_readme_is_a_short_quickstart():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    snippet = (ROOT / "examples" / "standards.yml").read_text(encoding="utf-8").strip()
    assert snippet in readme
    assert "examples/cos.yaml" in readme
    assert "docs/checks.md" in readme
    assert snippet.count("contents: read") == 2
    assert len(readme.splitlines()) < 40


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
    assert "DEBIAN_FRONTEND: noninteractive" in verify
    assert "verify-receipt" in verify


def test_scanners_include_tests_and_build_dirs(tmp_path: Path):
    for name in ("tests", "build", "dist", ".venv", "node_modules"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "note.md").write_text("acme\n", encoding="utf-8")
    found = {path.relative_to(tmp_path).as_posix() for path in collect(tmp_path)}
    assert found == {
        "tests/note.md",
        "build/note.md",
        "dist/note.md",
        ".venv/note.md",
        "node_modules/note.md",
    }
