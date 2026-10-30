from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

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
    (base / "features").mkdir(parents=True, exist_ok=True)
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
    _script(tmp_path, "scripts/verify.py", body="print('ok')\n", mode=0o644)
    (tmp_path / "Makefile").write_text("verify:\n\tpython scripts/verify.py\n", encoding="utf-8")
    assert skill_problems(tmp_path) == []


def test_npm_script_passes(tmp_path: Path):
    command = "npm run verify"
    _tree(tmp_path, command=command)
    _script(tmp_path, "scripts/verify.js", body="console.log('ok')\n", mode=0o644)
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


def test_placeholder_section_body_fails_then_passes(tmp_path: Path):
    doctor = "Run `scripts/verify` and expect exit 0 before changing anything.\n"
    stubs = {
        "TBD\n": "section Doctor is only a placeholder",
        "TODO\n": "section Doctor is only a placeholder",
        ".\n": "section Doctor is only a placeholder",
        "<!-- soon -->\n": "section Doctor is only a placeholder",
        "\u200b\u200c\ufeff\n": "section Doctor is only a placeholder",
        "   \n": "empty section Doctor",
    }
    for stub, message in stubs.items():
        text = _skill_text("scripts/verify").replace(doctor, stub)
        _tree(tmp_path, skill=text)
        found = skill_problems(tmp_path)
        assert any(message in item for item in found), found
    _tree(tmp_path)
    feature = tmp_path / ".cursor" / "skills" / "verify-sample" / "features" / "build.md"
    feature.write_text(FEATURE.replace("- Write the output file.\n", "TODO\n"), encoding="utf-8")
    found = skill_problems(tmp_path)
    assert any("heading Sub-features is only a placeholder" in item for item in found), found
    _tree(tmp_path)
    assert skill_problems(tmp_path) == []


def test_slot_patterns_fail_then_pass(tmp_path: Path):
    doctor = "expect exit 0 before changing anything."
    slots = ["<TODO>", "<App>", "<APP>", "{{app}}", "< name >", "<evidence>", "<port>", "{{ PORT }}"]
    for slot in slots:
        text = _skill_text("scripts/verify").replace(doctor, f"{doctor} {slot}")
        _tree(tmp_path, skill=text)
        found = skill_problems(tmp_path)
        assert any("template slot" in item and slot in item for item in found), found
    _tree(tmp_path)
    feature = tmp_path / ".cursor" / "skills" / "verify-sample" / "features" / "build.md"
    feature.write_text(FEATURE.replace("A person runs the script.", "A person runs the script. {{app}}"), encoding="utf-8")
    found = skill_problems(tmp_path)
    assert any("build.md" in item and "{{app}}" in item for item in found), found
    feature.write_text(FEATURE, encoding="utf-8")
    helper = tmp_path / ".cursor" / "skills" / "verify-sample" / "helper.py"
    helper.write_text("print('<port>')\n", encoding="utf-8")
    helper.chmod(0o755)
    skill = tmp_path / ".cursor" / "skills" / "verify-sample" / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8").replace("## Helpers\n", "## Helpers\n\nhelper.py\n"), encoding="utf-8")
    found = skill_problems(tmp_path)
    assert any("helper.py" in item and "<port>" in item for item in found), found
    helper.write_text("print('ok')\n", encoding="utf-8")
    assert skill_problems(tmp_path) == []


def test_cleanup_that_removes_evidence_fails_then_passes(tmp_path: Path):
    bad = _skill_text("scripts/verify").replace(
        "Remove scratch files. Do not delete `evidence/sample`.",
        "Do not delete scratch files. rm -rf `evidence/sample`.",
    )
    _tree(tmp_path, skill=bad)
    found = skill_problems(tmp_path)
    assert any("Cleanup removes the evidence path" in item for item in found), found
    _tree(tmp_path)
    assert skill_problems(tmp_path) == []


def test_verify_command_path_is_a_whole_token(tmp_path: Path):
    bad = _skill_text("scripts/verify").replace(
        "## Helpers\n\nRun `scripts/verify` from the repo root.\n",
        "## Helpers\n\nRun `not-scripts/verify` from the repo root.\n",
    )
    _tree(tmp_path, skill=bad)
    found = skill_problems(tmp_path)
    assert any("Helpers must show the verify command" in item for item in found), found
    good = _skill_text("scripts/verify").replace(
        "## Helpers\n\nRun `scripts/verify` from the repo root.\n",
        "## Helpers\n\nRun `./scripts/verify` from the repo root.\n",
    )
    _tree(tmp_path, skill=good)
    assert skill_problems(tmp_path) == []


def test_recipe_file_must_exist_then_pass(tmp_path: Path):
    _tree(tmp_path, command="npm run verify")
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"verify": "node scripts/verify.js"}}),
        encoding="utf-8",
    )
    found = skill_problems(tmp_path)
    assert any("scripts/verify.js" in item and "does not exist" in item for item in found), found
    _script(tmp_path, "scripts/verify.js", body="console.log('ok')\n", mode=0o644)
    assert skill_problems(tmp_path) == []
    made = tmp_path / "make-repo"
    made.mkdir()
    _tree(made, command="make verify")
    (made / "Makefile").write_text("verify:\n\tpython scripts/missing.py\n", encoding="utf-8")
    found = skill_problems(made)
    assert any("scripts/missing.py" in item and "does not exist" in item for item in found), found
    _script(made, "scripts/missing.py", body="print('ok')\n", mode=0o644)
    assert skill_problems(made) == []
    for folder, command in (("pnpm-repo", "pnpm verify"), ("yarn-repo", "yarn verify")):
        root = tmp_path / folder
        root.mkdir()
        _tree(root, command=command)
        (root / "package.json").write_text(
            json.dumps({"scripts": {"verify": "node scripts/verify.js"}}),
            encoding="utf-8",
        )
        assert any("does not exist" in item for item in skill_problems(root))
        _script(root, "scripts/verify.js", body="console.log('ok')\n", mode=0o644)
        assert skill_problems(root) == []


CLEANUP_LINE = "Remove scratch files. Do not delete `evidence/sample`."


@pytest.mark.parametrize(
    "cleanup",
    [
        "It removes `evidence/sample`.",
        "It deletes `evidence/sample`.",
        "It wipes `evidence/sample`.",
        "Schedule deletion of `evidence/sample`.",
        "Schedule deletion of the proof directory.",
        "rm -rf evidence/*",
        "It removes\n`evidence/sample`.",
    ],
)
def test_cleanup_removal_case_fails_then_passes(tmp_path: Path, cleanup: str):
    bad = _skill_text("scripts/verify").replace(CLEANUP_LINE, cleanup)
    _tree(tmp_path, skill=bad)
    found = skill_problems(tmp_path)
    assert any("Cleanup removes the evidence path" in item for item in found), found
    _tree(tmp_path)
    assert skill_problems(tmp_path) == []


def test_cleanup_do_not_ever_delete_keeps(tmp_path: Path):
    text = _skill_text("scripts/verify").replace(
        CLEANUP_LINE,
        "Remove scratch files. Do not ever delete `evidence/sample`.",
    )
    _tree(tmp_path, skill=text)
    assert skill_problems(tmp_path) == []


def test_make_var_path_must_exist_then_pass(tmp_path: Path):
    _tree(tmp_path, command="make verify")
    (tmp_path / "Makefile").write_text("verify:\n\t$(PY) scripts/missing.py\n", encoding="utf-8")
    found = skill_problems(tmp_path)
    assert any("scripts/missing.py" in item and "does not exist" in item for item in found), found
    _script(tmp_path, "scripts/missing.py", body="print('ok')\n", mode=0o644)
    assert skill_problems(tmp_path) == []


@pytest.mark.parametrize(
    "recipe",
    [
        "true",
        "echo ok",
        "#!/bin/sh\nexit 0",
    ],
)
def test_noop_recipe_fails_then_passes(tmp_path: Path, recipe: str):
    _tree(tmp_path, command="npm run verify")
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"verify": recipe}}),
        encoding="utf-8",
    )
    found = skill_problems(tmp_path)
    assert any("no-op" in item for item in found), found
    _script(tmp_path, "scripts/verify.js", body="console.log('ok')\n", mode=0o644)
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"verify": "node scripts/verify.js"}}),
        encoding="utf-8",
    )
    assert skill_problems(tmp_path) == []


@pytest.mark.parametrize(
    "stub",
    [
        "N/A",
        "???",
        "T.B.D.",
        "TO DO",
        "FIXME",
        "<!-- still unfinished and this comment never closes",
        "&#8203;",
    ],
)
def test_placeholder_word_fails_then_passes(tmp_path: Path, stub: str):
    doctor = "Run `scripts/verify` and expect exit 0 before changing anything.\n"
    text = _skill_text("scripts/verify").replace(doctor, stub + "\n")
    _tree(tmp_path, skill=text)
    found = skill_problems(tmp_path)
    assert any("section Doctor is only a placeholder" in item for item in found), found
    _tree(tmp_path)
    assert skill_problems(tmp_path) == []


@pytest.mark.parametrize(
    "slot",
    [
        "<123>",
        "<app/>",
        "{app}",
        "&lt;app&gt;",
        "\uFF1Capp\uFF1E",
        "\uFF5Bapp\uFF5D",
    ],
)
def test_slot_spelling_fails_then_passes(tmp_path: Path, slot: str):
    doctor = "expect exit 0 before changing anything."
    text = _skill_text("scripts/verify").replace(doctor, f"{doctor} {slot}")
    _tree(tmp_path, skill=text)
    found = skill_problems(tmp_path)
    assert any("template slot" in item for item in found), found
    _tree(tmp_path)
    fenced = _skill_text("scripts/verify").replace(
        doctor,
        doctor + "\n\n```\nprint('hello from the shell')\nvalue = 1\n```\n",
    )
    _tree(tmp_path, skill=fenced)
    assert skill_problems(tmp_path) == []


@pytest.mark.parametrize(
    ("cleanup", "evidence"),
    [
        ("Do not delete `evidence/verify-sample` during cleanup.", "evidence/verify-sample"),
        ("Never remove `evidence/x` when you run cleanup.", "evidence/x"),
        ("Do not clean `evidence/sample` during cleanup.", "evidence/sample"),
    ],
)
def test_cleanup_noun_keeps(tmp_path: Path, cleanup: str, evidence: str):
    text = _skill_text("scripts/verify").replace("evidence/sample", evidence)
    text = text.replace(f"Remove scratch files. Do not delete `{evidence}`.", cleanup)
    _tree(tmp_path, skill=text)
    assert skill_problems(tmp_path) == []


@pytest.mark.parametrize(
    "cleanup",
    [
        "Clean up `evidence/sample`.",
        "Cleans up `evidence/sample`.",
        "Cleaned up the proof.",
        "Cleaning up `evidence/sample`.",
    ],
)
def test_clean_up_on_the_evidence_path_fails(tmp_path: Path, cleanup: str):
    text = _skill_text("scripts/verify").replace(CLEANUP_LINE, cleanup)
    _tree(tmp_path, skill=text)
    found = skill_problems(tmp_path)
    assert any("Cleanup removes the evidence path" in item for item in found), found


@pytest.mark.parametrize(
    "cleanup",
    [
        "Clean-up `evidence/sample`.",
        "Cleans-up the proof.",
    ],
)
def test_hyphenated_clean_up_on_the_evidence_path_fails(tmp_path: Path, cleanup: str):
    text = _skill_text("scripts/verify").replace(CLEANUP_LINE, cleanup)
    _tree(tmp_path, skill=text)
    found = skill_problems(tmp_path)
    assert any("Cleanup removes the evidence path" in item for item in found), found


@pytest.mark.parametrize(
    "cleanup",
    [
        "Do not clean up `evidence/sample`.",
        "Do not clean-up `evidence/sample`.",
    ],
)
def test_do_not_clean_up_keeps(tmp_path: Path, cleanup: str):
    text = _skill_text("scripts/verify").replace(CLEANUP_LINE, cleanup)
    _tree(tmp_path, skill=text)
    assert skill_problems(tmp_path) == []


@pytest.mark.parametrize("verb", ["Clean", "Cleans", "Cleaned", "Cleaning"])
def test_clean_verb_on_the_evidence_path_fails(tmp_path: Path, verb: str):
    text = _skill_text("scripts/verify").replace(CLEANUP_LINE, f"{verb} `evidence/sample` during cleanup.")
    _tree(tmp_path, skill=text)
    found = skill_problems(tmp_path)
    assert any("Cleanup removes the evidence path" in item for item in found), found


@pytest.mark.parametrize(
    "extra",
    [
        "Read <https://example.com/health> once the server is ready for a person.",
        "The primary control is `<button>` on the main screen.",
        "The health payload looks like {status: active} before the page is ready.",
    ],
)
def test_ordinary_brackets_are_not_slots(tmp_path: Path, extra: str):
    doctor = "Run `scripts/verify` and expect exit 0 before changing anything."
    text = _skill_text("scripts/verify").replace(doctor, f"{doctor} {extra}")
    _tree(tmp_path, skill=text)
    assert skill_problems(tmp_path) == []


@pytest.mark.parametrize("tag", ["</script>", "</button>"])
def test_closing_tag_is_not_a_slot(tmp_path: Path, tag: str):
    doctor = "Run `scripts/verify` and expect exit 0 before changing anything."
    text = _skill_text("scripts/verify").replace(doctor, f"{doctor} The page markup includes {tag} in the shell.")
    _tree(tmp_path, skill=text)
    assert skill_problems(tmp_path) == []


def test_helper_dict_is_not_a_slot(tmp_path: Path):
    _tree(tmp_path)
    helper = tmp_path / ".cursor" / "skills" / "verify-sample" / "helper.py"
    helper.write_text('payload = {"status": "active"}\nprint(payload)\n', encoding="utf-8")
    helper.chmod(0o755)
    skill = tmp_path / ".cursor" / "skills" / "verify-sample" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8").replace("## Helpers\n", "## Helpers\n\nhelper.py reads the payload.\n"),
        encoding="utf-8",
    )
    assert skill_problems(tmp_path) == []


@pytest.mark.parametrize(
    "stub",
    [
        "A placeholder guest fails the drive.",
        "See the script output before driving.",
        "The cell needs writing from inputs.",
        "Please refill later from the inputs.",
    ],
)
def test_short_section_with_a_content_word_passes(tmp_path: Path, stub: str):
    doctor = "Run `scripts/verify` and expect exit 0 before changing anything.\n"
    text = _skill_text("scripts/verify").replace(doctor, stub + "\n")
    _tree(tmp_path, skill=text)
    assert skill_problems(tmp_path) == []


@pytest.mark.parametrize(
    "stub",
    [
        "not implemented yet",
        "fill this later",
        "coming soon",
        "lorem ipsum",
        "see the script",
        "to be written",
        "not implemented",
        "This is not implemented yet.",
        "Not yet implemented.",
        "Coming soon please.",
        "Fill this in later.",
        "See the script please.",
        "To be written later.",
        "Placeholder text goes here.",
        "Still needs writing soon.",
        "Write this section later.",
    ],
)
def test_filler_section_fails_then_passes(tmp_path: Path, stub: str):
    doctor = "Run `scripts/verify` and expect exit 0 before changing anything.\n"
    text = _skill_text("scripts/verify").replace(doctor, stub + "\n")
    _tree(tmp_path, skill=text)
    found = skill_problems(tmp_path)
    assert any("section Doctor is only a placeholder" in item for item in found), found
    _tree(tmp_path)
    assert skill_problems(tmp_path) == []


def test_realistic_app_skill_passes(tmp_path: Path):
    _realistic_skill(tmp_path, "verify-caltrack", "browser", "scripts/verify")
    _script(tmp_path, "scripts/verify")
    assert skill_problems(tmp_path) == []


def test_realistic_vault_skill_passes(tmp_path: Path):
    _realistic_skill(tmp_path, "verify-vault", "workbook", "python scripts/build.py")
    _script(tmp_path, "scripts/build.py", body="print('verify-ok')\n", mode=0o644)
    assert skill_problems(tmp_path) == []


def _realistic_skill(root: Path, name: str, surface: str, command: str) -> None:
    skill = root / ".cursor" / "skills" / name
    (skill / "features").mkdir(parents=True)
    evidence = f"evidence/{name}"
    body = (
        "---\n"
        f"name: {name}\n"
        f'description: "Drive the {surface} the way a person does. Use when proving a change."\n'
        f"verify: {command}\n"
        "---\n"
        "\n"
        f"# Verify {name}\n"
        "\n"
        "## Launch\n"
        "\n"
        f"From the repo root, run `{command}` and wait until it prints ready. "
        "The server or the script must be usable, including its seed data.\n"
        "\n"
        "## Doctor\n"
        "\n"
        f"Run `{command} doctor`. It checks the build and that the port belongs to this run. "
        "Read <https://example.com/health> and the payload {status: active} before driving.\n"
        "\n"
        "## Drive\n"
        "\n"
        "Open the primary screen the way a person does. "
        "The main control is `<button>` with a visible label, not a coordinate.\n"
        "\n"
        "## Evidence\n"
        "\n"
        f"Save the command output and the resulting screen under `{evidence}`.\n"
        "\n"
        "## Cleanup\n"
        "\n"
        f"Stop only the process this run started. Do not delete `{evidence}` during cleanup.\n"
        "\n"
        "## Helpers\n"
        "\n"
        f"Run `{command}` from the repo root. helper.py reads the saved payload.\n"
    )
    (skill / "SKILL.md").write_text(body, encoding="utf-8")
    (skill / "features" / "README.md").write_text("# Features\n\n- [Primary](primary.md)\n", encoding="utf-8")
    (skill / "features" / "primary.md").write_text(
        "# Primary\n"
        "\n"
        "The main path a person takes.\n"
        "\n"
        "## Sub-features\n"
        "\n"
        "- Open the primary screen.\n"
        "- Complete the one action a person came to do.\n"
        "- Read the result on that same screen.\n"
        "\n"
        "## How to get to it (user POV)\n"
        "\n"
        "Open the product and go to the primary screen with no test-only route.\n"
        "\n"
        "## Driving it with shell\n"
        "\n"
        f"Run `{command}` and read the resulting file under `{evidence}`.\n"
        "\n"
        "## Gotchas\n"
        "\n"
        "If the seed data is missing, the drive fails. Record the reason here.\n",
        encoding="utf-8",
    )
    helper = skill / "helper.py"
    helper.write_text('payload = {"status": "active"}\nprint(payload)\n', encoding="utf-8")
    helper.chmod(0o755)


def test_description_must_be_long_enough_and_name_the_surface(tmp_path: Path):
    original = 'description: "Drive the sample from the shell. Use when proving a change to the sample."'
    short = _skill_text("scripts/verify").replace(original, 'description: "Use the shell"')
    _tree(tmp_path, skill=short)
    found = skill_problems(tmp_path)
    assert any("description is too short" in item for item in found), found
    vague = _skill_text("scripts/verify").replace(
        original,
        'description: "Prove the sample change before anyone sees it."',
    )
    _tree(tmp_path, skill=vague)
    found = skill_problems(tmp_path)
    assert any("description must name the surface" in item for item in found), found
    _tree(tmp_path)
    assert skill_problems(tmp_path) == []
