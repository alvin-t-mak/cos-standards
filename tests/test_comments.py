from pathlib import Path

from cos_standards.check_comments import js_problems, problems, python_problems, shell_problems

ROOT = Path(__file__).resolve().parents[1]
from cos_standards.cli import main


def _write(root: Path, name: str, source: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_hash_comment_fails():
    found = python_problems("note.py", "x = 1\n# note\n")
    assert len(found) == 1
    assert found[0].startswith("note.py:2:")
    assert "# note" in found[0]


def test_inline_hash_comment_fails():
    found = python_problems("note.py", "x = 1  # note\n")
    assert len(found) == 1
    assert "note.py:1:" in found[0]


def test_hash_inside_a_string_passes():
    source = 'url = "https://example.com/#section"\nvalue = """\n# not a comment\n"""\n'
    assert python_problems("note.py", source) == []


def test_module_and_function_docstrings_fail():
    source = '"""Module."""\n\ndef run():\n    """Run."""\n    return 1\n'
    found = python_problems("note.py", source)
    assert len(found) == 2
    assert all("docstring" in item for item in found)


def test_class_docstring_fails():
    source = "class Box:\n    \"\"\"A box.\"\"\"\n    size = 1\n"
    found = python_problems("note.py", source)
    assert len(found) == 1
    assert "docstring" in found[0]


def test_string_statement_fails():
    source = "x = 1\n\"\"\"left behind\"\"\"\n"
    found = python_problems("note.py", source)
    assert len(found) == 1
    assert "docstring" in found[0]


def test_docstring_passed_to_a_call_stays():
    source = (
        '"""Help."""\n'
        "def run():\n"
        '    """Inner."""\n'
        "    return 1\n"
        "import argparse\n"
        "argparse.ArgumentParser(description=__doc__)\n"
    )
    found = python_problems("note.py", source)
    assert len(found) == 1
    assert "docstring" in found[0]
    assert found[0].startswith("note.py:3:")


def test_named_doc_passed_to_a_call_stays():
    source = "def run():\n    \"\"\"Inner.\"\"\"\n    tool(run.__doc__)\n"
    assert python_problems("note.py", source) == []


def test_type_ignore_and_noqa_stay():
    source = "import yaml  # type: ignore[attr-defined]\nx = 1  # noqa: E501, F401\n"
    assert python_problems("note.py", source) == []


def test_directive_with_a_reason_fails():
    found = python_problems("note.py", "import yaml  # type: ignore missing stubs\n")
    assert len(found) == 1


def test_shebang_and_encoding_stay():
    source = "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\nvalue = 1\n"
    assert python_problems("note.py", source) == []


def test_lint_ignore_file_stays():
    source = "# lint: ignore-file\nvalue = 1\n"
    assert python_problems("note.py", source) == []


def test_lint_ignore_with_a_reason_fails():
    found = python_problems("note.py", "# lint: ignore-file quotes banned text\nvalue = 1\n")
    assert len(found) == 1


def test_python_syntax_error_fails():
    found = python_problems("note.py", "def (\n")
    assert found == ["note.py:1: cannot parse"]


def test_js_line_and_block_comments_fail():
    source = "const value = 1;\n// note\nconst other = 2; /* also */\n"
    found = js_problems("note.js", source)
    assert len(found) == 2
    assert found[0].startswith("note.js:2:")
    assert found[1].startswith("note.js:3:")


def test_js_url_string_regex_and_division_pass():
    source = "\n".join([
        'const url = "https://example.com";',
        "const pattern = /https?:\\/\\//;",
        "const value = a / b / c;",
        "const again = a / /b/;",
        "return /ok/;",
        "const text = `https://example.com/${id}`;",
        "function run() {",
        '  const inner = "https://example.com/a";',
        "  if (ok) {",
        "    const nested = 1;",
        "  }",
        "}",
        "",
    ])
    assert js_problems("note.js", source) == []


def test_js_comment_inside_nested_blocks_fails():
    source = "\n".join([
        "function run() {",
        '  const url = "https://example.com";',
        "  // hidden",
        "  if (ok) {",
        "    const other = 1;",
        "  }",
        "  // also",
        "}",
        "",
    ])
    found = js_problems("note.js", source)
    assert [item.split(":")[1] for item in found] == ["3", "7"]


def test_eslint_and_ts_expect_error_stay():
    source = "\n".join([
        "// eslint-disable-next-line no-console",
        "console.log(1);",
        "/* eslint-disable no-console */",
        "// @ts-expect-error 2345",
        "const value = 1;",
        "",
    ])
    assert js_problems("note.ts", source) == []


def test_ts_expect_error_with_a_sentence_fails():
    found = js_problems("note.ts", "// @ts-expect-error the stub is wrong\nconst value = 1;\n")
    assert len(found) == 1


def test_tsx_text_generics_and_jsx_comments():
    clean = "\n".join([
        "export function View() {",
        '  return <a href="https://example.com">see https://example.com</a>;',
        "}",
        "const items: Array<string> = [];",
        "const node = <img />;",
        "",
    ])
    assert js_problems("view.tsx", clean, jsx=True) == []
    commented = "const node = <div>{/* note */}</div>;\n// later\n"
    found = js_problems("view.tsx", commented, jsx=True)
    assert len(found) == 2


def test_js_shebang_stays():
    source = "#!/usr/bin/env node\nconst value = 1;\n"
    assert js_problems("note.js", source) == []


def test_shell_comment_fails_and_shebang_stays():
    source = "#!/usr/bin/env bash\necho ok\n# note\n"
    found = shell_problems("run.sh", source)
    assert len(found) == 1
    assert found[0].startswith("run.sh:3:")
    assert "# note" in found[0]


def test_shell_quotes_params_and_heredoc_pass():
    source = "\n".join([
        "#!/bin/sh",
        'echo "hash # inside"',
        "echo 'hash # inside'",
        'echo "${name#prefix}"',
        'echo "$#"',
        "cat <<EOF",
        "# data",
        "EOF",
        "cat<<END",
        "# more data",
        "END",
        "echo done",
        "",
    ])
    assert shell_problems("run.sh", source) == []


def test_shell_comment_after_code_fails():
    found = shell_problems("run.sh", "echo done # note\n")
    assert len(found) == 1


def test_walk_skips_dependencies_and_reads_source(tmp_path: Path):
    _write(tmp_path, "src/app.py", "value = 1  # note\n")
    _write(tmp_path, "node_modules/pkg/index.js", "const value = 1; // vendor\n")
    _write(tmp_path, ".venv/lib/site.py", "# vendor\n")
    _write(tmp_path, "dist/out.js", "// built\n")
    _write(tmp_path, "build/out.js", "// built\n")
    found = problems(tmp_path)
    assert len(found) == 1
    assert found[0].startswith("src/app.py:1:")


def test_shebang_selects_the_language(tmp_path: Path):
    _write(tmp_path, "tools/render", "#!/usr/bin/env python3\n# note\n")
    _write(tmp_path, "tools/serve", "#!/usr/bin/env node\n// note\n")
    _write(tmp_path, "tools/run", "#!/usr/bin/env bash\n# note\n")
    found = problems(tmp_path)
    assert len(found) == 3
    assert {item.split(":")[0] for item in found} == {"tools/render", "tools/serve", "tools/run"}


def test_tool_directives_on_their_own_line_stay():
    source = "\n".join([
        "# fmt: off",
        "# pragma: no cover",
        "# pylint: disable=missing-docstring",
        "# pyright: ignore[reportUnused]",
        "# ruff: noqa: E501",
        "# mypy: ignore-errors",
        "# nosec B101",
        "# isort: skip_file",
        "value = 1",
        "",
    ])
    assert python_problems("note.py", source) == []


def test_this_repo_has_no_comments():
    assert problems(ROOT) == []


def test_cos_lint_fails_on_a_comment(tmp_path: Path):
    _write(tmp_path, "note.py", "value = 1  # note\n")
    assert main(["--root", str(tmp_path)]) == 1


def test_cos_lint_passes_a_repo_with_no_comments(tmp_path: Path):
    _write(tmp_path, "note.py", "value = 1\n")
    _write(tmp_path, "web/app.ts", 'const url = "https://example.com";\n')
    _write(tmp_path, "run.sh", "#!/bin/sh\necho ok\n")
    assert main(["--root", str(tmp_path)]) == 0
