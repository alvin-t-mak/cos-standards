"""Local config can add rules and tighten caps. It cannot turn a check off."""
from __future__ import annotations

from pathlib import Path

import pytest

from cos_standards.config import load_config
from cos_standards.errors import StandardsError

ROOT = Path(__file__).resolve().parents[1]


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "cos.yaml"
    path.write_text("version: 1\n" + body, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "body",
    [
        "enabled: false\n",
        "strict: false\n",
        "generated: false\n",
        "skip: [writing-lint]\n",
        "exempt: true\n",
        "outward:\n  folders: []\n  terms: []\n  omit_logo: []\n",
        "outward:\n  folders: []\n  terms: []\n  allow: []\n",
        "slack:\n  max_lines: 6\n",
        "vendor_notes:\n  max_bullets: 5\n",
        "vendor_notes:\n  max_words: 26\n",
        "format:\n  dates:\n    enabled: true\n",
    ],
)
def test_disabling_keys_are_rejected(tmp_path: Path, body: str):
    path = _write(tmp_path, body)
    with pytest.raises(StandardsError):
        load_config(str(path), tmp_path)


def test_stricter_caps_are_accepted(tmp_path: Path):
    path = _write(
        tmp_path,
        "slack:\n  max_lines: 3\nvendor_notes:\n  max_bullets: 2\n  max_words: 10\n",
    )
    config = load_config(str(path), tmp_path)
    assert config.slack_max_lines == 3
    assert config.vendor_max_bullets == 2
    assert config.vendor_max_words == 10


def test_missing_paths_add_nothing(tmp_path: Path):
    path = _write(
        tmp_path,
        "notion_paths:\n  - Product/\noutward:\n  folders:\n    - GTM\n  terms:\n    - zz-local-term\nrules: standards/rules.yaml\ncorrections: standards/corrections.yaml\nmodels: standards/models.yaml\n",
    )
    config = load_config(str(path), tmp_path)
    assert config.notion_paths == ["Product/"]
    assert config.outward_folders == ["GTM"]
    assert config.rules_path == tmp_path / "standards" / "rules.yaml"
    assert not config.rules_path.exists()


def test_shared_banned_id_cannot_be_replaced(tmp_path: Path):
    path = _write(
        tmp_path,
        """extra_banned:
  - id: em-dash
    category: punctuation
    type: literal
    pattern: "nope"
    severity: error
    reason: replace
""",
    )
    with pytest.raises(StandardsError, match="collides"):
        load_config(str(path), tmp_path)


def test_example_config_adds_a_term():
    config = load_config(str(ROOT / "examples" / "cos.yaml"), ROOT)
    assert "em-dash" in config.banned_ids
    assert "repo-specific-term" in config.banned_ids
    assert config.slack_max_lines == 5
    assert config.vendor_max_bullets == 4
