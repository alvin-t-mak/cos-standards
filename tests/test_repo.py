"""The repo lints itself, and the consumer contract stays in the README."""

from pathlib import Path

from cos_standards.check_generated import check_mirrors
from cos_standards.cli import main
from cos_standards.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def test_repo_lints_clean():
    assert main(["--root", str(ROOT)]) == 0


def test_generated_mirrors_match():
    assert check_mirrors(ROOT) == []


def test_readme_embeds_the_consumer_contract():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in (
        "examples/standards.yml",
        "examples/cos.yaml",
        "examples/rules.yaml",
        "examples/corrections.yaml",
    ):
        snippet = (ROOT / name).read_text(encoding="utf-8").strip()
        assert snippet in readme, name
    assert "uses: alvin-t-mak/cos-standards/.github/workflows/lint.yml@main" in readme
    assert 'pip install "cos-standards @ git+https://github.com/alvin-t-mak/cos-standards"' in readme


def test_reusable_workflow_is_call_only():
    text = (ROOT / ".github/workflows/lint.yml").read_text(encoding="utf-8")
    assert "workflow_call:" in text
    assert "pull_request:" not in text
    assert "git+https://github.com/alvin-t-mak/cos-standards@" in text
    assert "cos-lint" in text


def test_example_config_adds_and_keeps_shared_rules():
    config = load_config(str(ROOT / "examples/cos.yaml"), ROOT, check_paths=False)
    assert "em-dash" in config.banned_ids
    assert "repo-specific-term" in config.banned_ids
    assert config.lookups_enabled is True
    assert "VLOOKUP" not in {name.casefold() for name in config.extra_lookups}


def test_public_tree_has_no_private_detail():
    banned = ("lightfield", "attio", "tryalma", "faction.ai", "alvin@", "veroa.ai")
    skip = {".git", "_src", "__pycache__", ".pytest_cache", ".venv", "tests", "dist", "build"}
    leaks: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in skip or part.endswith(".egg-info") for part in path.parts):
            continue
        if path.suffix.lower() in {".png", ".pyc"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lowered = text.casefold()
        for needle in banned:
            if needle in lowered:
                leaks.append(f"{needle} in {path}")
        if "veroa" in lowered.replace("veroa-vault", ""):
            leaks.append(f"veroa in {path}")
    assert leaks == []
