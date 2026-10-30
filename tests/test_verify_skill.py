from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path

from cos_standards.check_verify import command_problem, main as verify_main
from cos_standards.check_verify import problems, skill_problems
from cos_standards.cli import main as lint_main

ROOT = Path(__file__).resolve().parents[1]
PASS = ROOT / "tests" / "fixtures" / "verify-skill" / "pass"
FAIL = ROOT / "tests" / "fixtures" / "verify-skill" / "fail"

APP_SLOTS = (
    ("<evidence-dir>", "evidence/sample"),
    ("<ready-line>", "ready"),
    ("<command>", "scripts/verify"),
    ("<script>", "scripts/verify"),
    ("<surface>", "cli"),
    ("<harness>", "shell"),
    ("<feature>", "primary"),
    ("<app>", "sample"),
)
VAULT_SLOTS = (
    ("<evidence-dir>", "evidence/sample"),
    ("<ready-line>", "verify-ok"),
    ("<command>", "python scripts/verify.py"),
    ("<script>", "scripts/verify.py"),
    ("<surface>", "cli"),
    ("<harness>", "python"),
    ("<feature>", "primary"),
    ("<app>", "sample"),
)


def _skill_text(command: str) -> str:
    return (
        "---\n"
        "name: verify-sample\n"
        'description: "Drive the sample from the shell. Use when proving a change to the sample."\n'
        f"verify: {command}\n"
        "---\n"
        "\n"
        "# Verify sample\n"
        "\n"
        "## Launch\n"
        "\n"
        f"Run `{command}` from the repo root. Ready means it printed verify-ok.\n"
        "\n"
        "## Doctor\n"
        "\n"
        f"Run `{command}` and expect exit 0 before changing anything.\n"
        "\n"
        "## Drive\n"
        "\n"
        f"Run `{command}` and read the result a person would read.\n"
        "\n"
        "## Evidence\n"
        "\n"
        "Write the proof under `evidence/sample`.\n"
        "\n"
        "## Cleanup\n"
        "\n"
        "Remove scratch files. Do not delete `evidence/sample`.\n"
        "\n"
        "## Helpers\n"
        "\n"
        f"Run `{command}` from the repo root.\n"
    )


FEATURE = """\
# Build

A person runs the script.

## Sub-features

- Write the output file.

## How to get to it (user POV)

From the repo root, run the verify command.

## Driving it with shell

Run the verify command. The end state is the output file, and the proof is under `evidence/sample`.

## Gotchas

If the input is missing, the drive fails. Do not skip the check to make the run pass.
"""


def _script(root: Path, relative: str = "scripts/verify", *, body: str | None = None, mode: int = 0o755) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if body is None:
        body = "#!/usr/bin/env bash\necho verify-ok\n" if not relative.endswith(".py") else "print('verify-ok')\n"
    path.write_text(body, encoding="utf-8")
    path.chmod(mode)
    return path


def _tree(root: Path, command: str = "scripts/verify", skill: str | None = None) -> None:
    base = root / ".cursor" / "skills" / "verify-sample"
    (base / "features").mkdir(parents=True)
    (base / "SKILL.md").write_text(skill or _skill_text(command), encoding="utf-8")
    (base / "features" / "README.md").write_text("# Features\n\n- [Build](build.md)\n", encoding="utf-8")
    (base / "features" / "build.md").write_text(FEATURE, encoding="utf-8")
    if command == "scripts/verify":
        _script(root)


def _fill(src: Path, dest: Path, slots: tuple[tuple[str, str], ...]) -> str:
    command = ""
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for key, value in slots:
            text = text.replace(key, value)
        target = dest / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        if path.name == "SKILL.md":
            for line in text.splitlines():
                if line.startswith("verify:"):
                    command = line.split(":", 1)[1].strip()
    return command


def _materialize(root: Path, command: str) -> None:
    relative = next(part for part in shlex.split(command) if "/" in part)
    if relative.endswith(".py"):
        _script(root, relative, body="print('verify-ok')\n", mode=0o644)
        return
    _script(root, relative)


def test_pass_fixture_has_no_problems():
    assert skill_problems(PASS) == []
    assert verify_main(["--root", str(PASS)]) == 0
    assert lint_main(["--root", str(PASS)]) == 0


def test_fail_fixture_lacks_a_skill():
    found = skill_problems(FAIL)
    assert any("no verify skill" in item for item in found)
    assert verify_main(["--root", str(FAIL)]) == 1
    assert lint_main(["--root", str(FAIL)]) == 1


def test_package_repo_is_skipped():
    assert problems(ROOT) == []
    assert any("no verify skill" in item for item in skill_problems(ROOT))
    assert verify_main(["--root", str(ROOT)]) == 0


def test_pass_fixture_command_keeps_evidence(tmp_path: Path):
    dest = tmp_path / "pass"
    shutil.copytree(PASS, dest)
    script = dest / "scripts" / "verify"
    script.chmod(script.stat().st_mode | 0o755)
    completed = subprocess.run([str(script), "cleanup"], cwd=dest, check=True, capture_output=True, text=True)
    assert "cleanup-ok" in completed.stdout
    proof = dest / "evidence" / "verify-sample" / "sample.txt"
    assert proof.read_text(encoding="utf-8") == "status=active\n"
    assert not (dest / "outputs").exists()


def test_valid_tree_passes(tmp_path: Path):
    _tree(tmp_path)
    assert skill_problems(tmp_path) == []


def test_missing_section_fails(tmp_path: Path):
    _tree(tmp_path)
    path = tmp_path / ".cursor" / "skills" / "verify-sample" / "SKILL.md"
    path.write_text(path.read_text(encoding="utf-8").replace("## Doctor\n\n", ""), encoding="utf-8")
    found = skill_problems(tmp_path)
    assert any("missing section Doctor" in item for item in found)


def test_empty_section_fails(tmp_path: Path):
    text = _skill_text("scripts/verify").replace(
        "Run `scripts/verify` and expect exit 0 before changing anything.\n",
        "",
    )
    _tree(tmp_path, skill=text)
    found = skill_problems(tmp_path)
    assert any("empty section Doctor" in item for item in found)


def test_section_order_fails(tmp_path: Path):
    text = _skill_text("scripts/verify").replace("## Launch", "## Later").replace("## Doctor", "## Launch").replace(
        "## Later", "## Doctor"
    )
    _tree(tmp_path, skill=text)
    found = skill_problems(tmp_path)
    assert any("sections out of order" in item for item in found)


def test_name_must_match_the_directory(tmp_path: Path):
    text = _skill_text("scripts/verify").replace("name: verify-sample", "name: verify-other")
    _tree(tmp_path, skill=text)
    found = skill_problems(tmp_path)
    assert any("name must be verify-sample" in item for item in found)


def test_missing_script_fails(tmp_path: Path):
    _tree(tmp_path)
    (tmp_path / "scripts" / "verify").unlink()
    found = skill_problems(tmp_path)
    assert any("does not exist" in item for item in found)


def test_script_must_be_executable(tmp_path: Path):
    _tree(tmp_path)
    (tmp_path / "scripts" / "verify").chmod(0o644)
    found = skill_problems(tmp_path)
    assert any("not executable" in item for item in found)


def test_script_needs_a_shebang(tmp_path: Path):
    _tree(tmp_path)
    _script(tmp_path, body="echo verify-ok\n", mode=0o755)
    found = skill_problems(tmp_path)
    assert any("needs a shebang" in item for item in found)


def test_chained_command_fails(tmp_path: Path):
    command = "scripts/verify && scripts/verify"
    _tree(tmp_path, command=command)
    _script(tmp_path)
    found = skill_problems(tmp_path)
    assert any("single command" in item for item in found)


def test_python_script_does_not_need_the_executable_bit(tmp_path: Path):
    command = "python scripts/verify.py"
    _tree(tmp_path, command=command)
    _script(tmp_path, "scripts/verify.py", body="print('verify-ok')\n", mode=0o644)
    assert skill_problems(tmp_path) == []


def test_make_target_passes(tmp_path: Path):
    command = "make verify"
    _tree(tmp_path, command=command)
    (tmp_path / "Makefile").write_text("verify:\n\ttrue\n", encoding="utf-8")
    assert skill_problems(tmp_path) == []


def test_npm_script_passes(tmp_path: Path):
    command = "npm run verify"
    _tree(tmp_path, command=command)
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"verify": "node scripts/verify.js"}}),
        encoding="utf-8",
    )
    assert skill_problems(tmp_path) == []


def test_uv_run_prefix_passes(tmp_path: Path):
    command = "uv run python scripts/verify.py"
    _tree(tmp_path, command=command)
    _script(tmp_path, "scripts/verify.py", body="print('verify-ok')\n", mode=0o644)
    assert skill_problems(tmp_path) == []


def test_template_slot_fails(tmp_path: Path):
    text = _skill_text("scripts/verify").replace("the sample", "<app>", 1)
    _tree(tmp_path, skill=text)
    found = skill_problems(tmp_path)
    assert any("template slot <app>" in item for item in found)


def test_cleanup_must_name_the_evidence(tmp_path: Path):
    text = _skill_text("scripts/verify").replace("Do not delete `evidence/sample`.", "Remove `outputs/sample`.")
    _tree(tmp_path, skill=text)
    found = skill_problems(tmp_path)
    assert any("same evidence/ path" in item for item in found)
    assert any("do not delete" in item for item in found)


def test_unlinked_feature_fails(tmp_path: Path):
    _tree(tmp_path)
    extra = tmp_path / ".cursor" / "skills" / "verify-sample" / "features" / "other.md"
    extra.write_text(FEATURE, encoding="utf-8")
    found = skill_problems(tmp_path)
    assert any("does not link other.md" in item for item in found)


def test_feature_heading_fails(tmp_path: Path):
    _tree(tmp_path)
    path = tmp_path / ".cursor" / "skills" / "verify-sample" / "features" / "build.md"
    path.write_text(FEATURE.replace("## Gotchas\n\nIf the input is missing, the drive fails. Do not skip the check to make the run pass.\n", ""), encoding="utf-8")
    found = skill_problems(tmp_path)
    assert any("missing heading Gotchas" in item for item in found)


def test_helper_must_be_named_and_executable(tmp_path: Path):
    _tree(tmp_path)
    helper = tmp_path / ".cursor" / "skills" / "verify-sample" / "helper.py"
    helper.write_text("print('verify-ok')\n", encoding="utf-8")
    helper.chmod(0o644)
    found = skill_problems(tmp_path)
    assert any("helper.py: helper is not named in SKILL.md" in item for item in found)
    assert any("helper.py: helper is not executable" in item for item in found)


def test_second_skill_must_also_pass(tmp_path: Path):
    _tree(tmp_path)
    other = tmp_path / ".cursor" / "skills" / "verify-other"
    other.mkdir()
    (other / "SKILL.md").write_text("hello\n", encoding="utf-8")
    assert skill_problems(tmp_path)


def test_filled_app_template_passes(tmp_path: Path):
    dest = tmp_path / ".cursor" / "skills" / "verify-sample"
    command = _fill(ROOT / "examples" / "verify-app", dest, APP_SLOTS)
    _materialize(tmp_path, command)
    assert skill_problems(tmp_path) == []


def test_filled_vault_template_passes(tmp_path: Path):
    dest = tmp_path / ".cursor" / "skills" / "verify-sample"
    command = _fill(ROOT / "examples" / "verify-vault", dest, VAULT_SLOTS)
    _materialize(tmp_path, command)
    assert skill_problems(tmp_path) == []


def test_unfilled_template_fails(tmp_path: Path):
    dest = tmp_path / ".cursor" / "skills" / "verify-app"
    shutil.copytree(ROOT / "examples" / "verify-app", dest)
    found = skill_problems(tmp_path)
    assert any("template slot" in item for item in found)


def test_command_cannot_escape_the_repo(tmp_path: Path):
    assert command_problem(tmp_path, "scripts/../../etc/passwd")
    assert command_problem(tmp_path, "/tmp/verify")
    assert command_problem(tmp_path, "true") is not None
