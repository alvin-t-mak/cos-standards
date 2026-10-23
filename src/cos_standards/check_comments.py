from __future__ import annotations

import argparse
import ast
import io
import os
import re
import sys
import tokenize
from pathlib import Path

PYTHON_EXTS = {".py", ".pyi", ".pyw"}
JS_EXTS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}
JSX_EXTS = {".jsx", ".tsx"}
SHELL_EXTS = {".sh", ".bash", ".zsh", ".ksh"}
SKIP_DIRS = {
    ".eggs",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "site-packages",
    "venv",
}
HASH_DIRECTIVES = (
    re.compile(r"type:[ \t]*ignore(?:\[[ \t]*[A-Za-z0-9_\-]+(?:[ \t]*,[ \t]*[A-Za-z0-9_\-]+)*[ \t]*\])?"),
    re.compile(r"noqa(?::[ \t]*[A-Za-z0-9]+(?:[ \t]*,[ \t]*[A-Za-z0-9]+)*)?"),
    re.compile(r"pragma:[ \t]*no[ \t]+cover"),
    re.compile(r"pylint:[ \t]*(?:disable|enable)(?:=[A-Za-z0-9_\-]+(?:,[A-Za-z0-9_\-]+)*)?"),
    re.compile(r"pyright:[ \t]*ignore(?:\[[ \t]*[A-Za-z0-9_\-]+(?:[ \t]*,[ \t]*[A-Za-z0-9_\-]+)*[ \t]*\])?"),
    re.compile(r"ruff:[ \t]*noqa(?::[ \t]*[A-Za-z0-9]+(?:[ \t]*,[ \t]*[A-Za-z0-9]+)*)?"),
    re.compile(
        r"mypy:[ \t]*(?:ignore-errors"
        r'|disable-error-code="[A-Za-z0-9_\-]+"'
        r'|enable-error-code="[A-Za-z0-9_\-]+")'
    ),
    re.compile(r"fmt:[ \t]*(?:off|on|skip)"),
    re.compile(r"lint:[ \t]*ignore(?:-file)?"),
    re.compile(r"nosec(?:[ \t]+[A-Za-z][A-Za-z0-9]*)?"),
    re.compile(r"isort:[ \t]*(?:skip_file|skip|off|on|split|dont-add-import(?::[A-Za-z0-9_.,]+)?)"),
)
CODING_DIRECTIVE = re.compile(
    r"(?:-\*-[ \t]*)?coding[:=][ \t]*[A-Za-z0-9_.\-]+(?:[ \t]*-\*-)?"
    r"|vim:[ \t]*set[ \t]+fileencoding=[A-Za-z0-9_.\-]+[ \t]*:?"
)
SLASH_DIRECTIVE = re.compile(
    r"eslint-disable(?:-next-line|-line)?(?:[ \t]+[A-Za-z0-9_@/.\-]+(?:,[ \t]*[A-Za-z0-9_@/.\-]+)*)?"
    r"|eslint-enable(?:[ \t]+[A-Za-z0-9_@/.\-]+(?:,[ \t]*[A-Za-z0-9_@/.\-]+)*)?"
    r"|@ts-(?:expect-error|ignore|nocheck|check)(?:[ \t]+(?:TS)?\d+)?"
    r"|prettier-ignore"
    r"|istanbul[ \t]+ignore[ \t]+(?:next|if|else|file)"
)
SHELL_SHEBANG = re.compile(r"^#!.*\b(?:sh|bash|zsh|ksh|dash)\b")
PYTHON_SHEBANG = re.compile(r"^#!.*\bpython[0-9.]*\b")
NODE_SHEBANG = re.compile(r"^#!.*\bnode\b")
JS_BEFORE_JSX = {"return", "yield", "throw", "case", "else", "void", "typeof", "new", "await", "extends"}
JS_EXPR_WORDS = JS_BEFORE_JSX | {"do", "delete", "in", "of", "instanceof"}
HEREDOC_MARK = re.compile(r"<<-?[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def problems(root: Path) -> list[str]:
    root = root.resolve()
    found: list[str] = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(name for name in dirs if not _skip_dir(name))
        for name in sorted(files):
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                first = ""
                kind = _kind(path, first)
                if kind is not None:
                    found.append(f"{rel}:1: cannot read as text")
                continue
            except OSError:
                continue
            first = text.splitlines()[0] if text.splitlines() else ""
            kind = _kind(path, first)
            if kind == "python":
                found.extend(python_problems(rel, text))
            elif kind == "js":
                found.extend(js_problems(rel, text, jsx=path.suffix.lower() in JSX_EXTS))
            elif kind == "shell":
                found.extend(shell_problems(rel, text))
    return found


def python_problems(rel: str, source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"{rel}:{exc.lineno or 1}: cannot parse"]
    return _python_comments(rel, source) + _python_docstrings(rel, tree)


def js_problems(rel: str, source: str, *, jsx: bool = False) -> list[str]:
    return _JS(rel, source, jsx).scan()


def shell_problems(rel: str, source: str) -> list[str]:
    return _scan_shell(rel, source)


def _skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.endswith(".egg-info")


def _kind(path: Path, first: str) -> str | None:
    ext = path.suffix.lower()
    if ext in PYTHON_EXTS:
        return "python"
    if ext in JS_EXTS:
        return "js"
    if ext in SHELL_EXTS:
        return "shell"
    if SHELL_SHEBANG.match(first):
        return "shell"
    if PYTHON_SHEBANG.match(first):
        return "python"
    if NODE_SHEBANG.match(first):
        return "js"
    return None


def _hash_directive(body: str, line: int) -> bool:
    if line <= 2 and CODING_DIRECTIVE.fullmatch(body):
        return True
    return any(pattern.fullmatch(body) for pattern in HASH_DIRECTIVES)


def _allowed_hash_comment(text: str, line: int) -> bool:
    if line == 1 and text.startswith("#!"):
        return True
    if not text.startswith("#"):
        return False
    return _hash_directive(text[1:].strip(), line)


def _python_comments(rel: str, source: str) -> list[str]:
    found = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in tokens:
            if tok.type != tokenize.COMMENT:
                continue
            if _allowed_hash_comment(tok.string, tok.start[0]):
                continue
            found.append(f"{rel}:{tok.start[0]}:{tok.start[1] + 1}: {tok.string.strip()}")
    except tokenize.TokenError:
        return [f"{rel}:1: cannot parse"]
    return found


def _string_statement(node: ast.AST) -> bool:
    return isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and isinstance(node.value.value, str)


def _doc_names(tree: ast.AST) -> tuple[bool, set[str]]:
    module = False
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        values = list(node.args)
        values.extend(keyword.value for keyword in node.keywords)
        for value in values:
            if isinstance(value, ast.Name) and value.id == "__doc__":
                module = True
            elif isinstance(value, ast.Attribute) and value.attr == "__doc__" and isinstance(value.value, ast.Name):
                names.add(value.value.id)
    return module, names


def _kept_doc_lines(tree: ast.AST) -> set[int]:
    module_used, names = _doc_names(tree)
    kept: set[int] = set()

    def keep(node: ast.AST, allow: bool) -> None:
        body = getattr(node, "body", None)
        if not allow or not body or not _string_statement(body[0]):
            return
        kept.add(body[0].lineno)

    keep(tree, module_used)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            keep(node, node.name in names)
    return kept


def _python_docstrings(rel: str, tree: ast.AST) -> list[str]:
    kept = _kept_doc_lines(tree)
    found = []
    for node in ast.walk(tree):
        if _string_statement(node) and node.lineno not in kept:
            found.append(f"{rel}:{node.lineno}:{node.col_offset + 1}: docstring")
    return found


def _slash_directive(body: str) -> bool:
    return SLASH_DIRECTIVE.fullmatch(body.strip()) is not None


def _block_body(text: str) -> str:
    inner = text
    if inner.startswith("/*"):
        inner = inner[2:]
    if inner.endswith("*/"):
        inner = inner[:-2]
    parts = []
    for line in inner.splitlines():
        stripped = line.strip()
        if stripped.startswith("*"):
            stripped = stripped[1:].strip()
        if stripped:
            parts.append(stripped)
    return " ".join(parts).strip()


class _JS:
    def __init__(self, rel: str, source: str, jsx: bool) -> None:
        self.rel = rel
        self.source = source
        self.n = len(source)
        self.jsx = jsx
        self.i = 0
        self.line = 1
        self.col = 1
        self.prev_word = ""
        self.prev_char = ""
        self.hits: list[str] = []

    def scan(self) -> list[str]:
        self._code(stop_brace=False)
        return self.hits

    def _peek(self, offset: int = 0) -> str:
        index = self.i + offset
        if index < 0 or index >= self.n:
            return ""
        return self.source[index]

    def _bump(self) -> str:
        char = self.source[self.i]
        self.i += 1
        if char == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return char

    def _mark(self, char: str) -> None:
        if char not in " \t\r\n":
            self.prev_char = char

    def _code(self, *, stop_brace: bool) -> None:
        while self.i < self.n:
            char = self._peek()
            if char in " \t\r\f":
                self._bump()
                continue
            if char == "\n":
                self._bump()
                continue
            if self.line == 1 and self.col == 1 and char == "#" and self._peek(1) == "!":
                while self.i < self.n and self._peek() != "\n":
                    self._bump()
                self.prev_word = ""
                self.prev_char = ""
                continue
            if char == "/" and self._peek(1) == "/":
                self._line_comment()
                continue
            if char == "/" and self._peek(1) == "*":
                self._block_comment()
                continue
            if char in "'\"":
                self._string(char)
                self.prev_word = ""
                self.prev_char = char
                continue
            if char == "`":
                self._template()
                continue
            if char == "/" and self._regex_or_jsx_or_div():
                continue
            if char == "/" :
                self._bump()
                self.prev_word = ""
                self.prev_char = "/"
                continue
            if char.isalpha() or char in "_$":
                self._word()
                continue
            if char.isdigit():
                self._number()
                continue
            if char == "{":
                self._bump()
                self.prev_word = ""
                self.prev_char = "{"
                self._code(stop_brace=True)
                continue
            if char == "}":
                if stop_brace:
                    return
                self._bump()
                self.prev_word = ""
                self.prev_char = "}"
                continue
            if char in "([":
                self._bump()
                self.prev_word = ""
                self.prev_char = char
                continue
            if char in ")]":
                self._bump()
                self.prev_word = ""
                self.prev_char = char
                continue
            if char == "<" and self._starts_jsx():
                self._jsx()
                continue
            if char == ".":
                self._bump()
                self.prev_word = ""
                self.prev_char = "."
                continue
            self._bump()
            self.prev_word = ""
            self._mark(char)
            self.prev_char = char

    def _line_comment(self) -> None:
        start_line, start_col = self.line, self.col
        self._bump()
        self._bump()
        chars: list[str] = []
        while self.i < self.n and self._peek() != "\n":
            chars.append(self._bump())
        body = "".join(chars).strip()
        if not _slash_directive(body):
            shown = body if body else "//"
            self.hits.append(f"{self.rel}:{start_line}:{start_col}: // {shown}".rstrip())
        self.prev_word = ""
        self.prev_char = ""

    def _block_comment(self) -> None:
        start_line, start_col = self.line, self.col
        self._bump()
        self._bump()
        chars: list[str] = []
        while self.i < self.n:
            if self._peek() == "*" and self._peek(1) == "/":
                self._bump()
                self._bump()
                break
            chars.append(self._bump())
        body = _block_body("/*" + "".join(chars) + "*/")
        if not _slash_directive(body):
            self.hits.append(f"{self.rel}:{start_line}:{start_col}: /* {body} */".rstrip())
        self.prev_word = ""
        self.prev_char = ""

    def _string(self, quote: str) -> None:
        self._bump()
        while self.i < self.n:
            char = self._bump()
            if char == "\\":
                if self.i < self.n:
                    self._bump()
                continue
            if char == quote or char == "\n":
                return

    def _template(self) -> None:
        self._bump()
        while self.i < self.n:
            char = self._peek()
            if char == "\\":
                self._bump()
                if self.i < self.n:
                    self._bump()
                continue
            if char == "`":
                self._bump()
                self.prev_word = ""
                self.prev_char = "`"
                return
            if char == "$" and self._peek(1) == "{":
                self._bump()
                self._bump()
                self.prev_word = ""
                self.prev_char = "{"
                self._code(stop_brace=True)
                if self.i < self.n and self._peek() == "}":
                    self._bump()
                continue
            self._bump()
        self.prev_word = ""
        self.prev_char = "`"

    def _can_start_regex(self) -> bool:
        if self.prev_word in JS_EXPR_WORDS:
            return True
        return self.prev_char == "" or self.prev_char in "([{:;,=!?&|~^%*+-<>/"

    def _regex_or_jsx_or_div(self) -> bool:
        if self._peek(1) in "/*":
            return False
        if self.jsx and self.prev_char == "<":
            self._bump()
            self.prev_word = ""
            self.prev_char = "/"
            return True
        if self.jsx and self._peek(1) == ">":
            self._bump()
            self._bump()
            self.prev_word = ""
            self.prev_char = ">"
            return True
        if not self._can_start_regex():
            self._bump()
            self.prev_word = ""
            self.prev_char = "/"
            return True
        self._regex()
        return True

    def _regex(self) -> None:
        self._bump()
        while self.i < self.n:
            char = self._peek()
            if char == "\\":
                self._bump()
                if self.i < self.n:
                    self._bump()
                continue
            if char == "[":
                self._bump()
                while self.i < self.n and self._peek() not in "]\n":
                    if self._peek() == "\\":
                        self._bump()
                        if self.i < self.n:
                            self._bump()
                        continue
                    self._bump()
                if self.i < self.n and self._peek() == "]":
                    self._bump()
                continue
            if char == "/":
                self._bump()
                break
            if char == "\n":
                break
            self._bump()
        while self.i < self.n and self._peek().isalpha():
            self._bump()
        self.prev_word = ""
        self.prev_char = "/"

    def _word(self) -> None:
        start = self.i
        self._bump()
        while self.i < self.n and (self._peek().isalnum() or self._peek() in "_$"):
            self._bump()
        word = self.source[start:self.i]
        self.prev_word = word
        self.prev_char = word[-1]

    def _number(self) -> None:
        self._bump()
        while self.i < self.n and (self._peek().isalnum() or self._peek() in "._"):
            self._bump()
        self.prev_word = ""
        self.prev_char = "0"

    def _starts_jsx(self) -> bool:
        if not self.jsx:
            return False
        nxt = self._peek(1)
        if not (nxt.isalpha() or nxt in "/_>" or nxt == ""):
            return False
        if nxt == "":
            return False
        if self.prev_word in JS_BEFORE_JSX:
            return True
        return self.prev_char in "([{:;,=!?&|>"

    def _jsx(self) -> None:
        kind = self._jsx_element()
        if kind == "self":
            return
        depth = 1
        while self.i < self.n and depth:
            char = self._peek()
            if char == "{":
                self._bump()
                self.prev_word = ""
                self.prev_char = "{"
                self._code(stop_brace=True)
                if self.i < self.n and self._peek() == "}":
                    self._bump()
                    self.prev_char = "}"
                continue
            if char == "<":
                child = self._jsx_element()
                if child == "open":
                    depth += 1
                elif child == "close":
                    depth -= 1
                continue
            if char in "'\"":
                self._string(char)
                continue
            self._bump()
        self.prev_word = ""
        self.prev_char = ">"

    def _jsx_element(self) -> str:
        self._bump()
        if self.i < self.n and self._peek() == ">":
            self._bump()
            self.prev_word = ""
            self.prev_char = ">"
            return "open"
        closing = False
        if self.i < self.n and self._peek() == "/":
            closing = True
            self._bump()
        while self.i < self.n and self._peek() not in " \t\r\n/>={'\"`":
            self._bump()
        if closing:
            while self.i < self.n and self._peek() != ">":
                self._bump()
            if self.i < self.n:
                self._bump()
            self.prev_word = ""
            self.prev_char = ">"
            return "close"
        while self.i < self.n:
            char = self._peek()
            if char in "'\"":
                self._string(char)
                continue
            if char == "{":
                self._bump()
                self.prev_word = ""
                self.prev_char = "{"
                self._code(stop_brace=True)
                if self.i < self.n and self._peek() == "}":
                    self._bump()
                continue
            if char == "/" and self._peek(1) == ">":
                self._bump()
                self._bump()
                self.prev_word = ""
                self.prev_char = ">"
                return "self"
            if char == ">":
                self._bump()
                self.prev_word = ""
                self.prev_char = ">"
                return "open"
            self._bump()
        return "open"


def _scan_shell(rel: str, source: str) -> list[str]:
    found: list[str] = []
    index = 0
    limit = len(source)
    line = 1
    col = 1
    word_start = True
    in_single = False
    in_double = False
    param_depth = 0

    def bump() -> str:
        nonlocal index, line, col
        char = source[index]
        index += 1
        if char == "\n":
            line += 1
            col = 1
        else:
            col += 1
        return char

    while index < limit:
        char = source[index]
        if in_single:
            bump()
            if char == "'":
                in_single = False
            word_start = False
            continue
        if in_double:
            if char == "\\" and index + 1 < limit:
                bump()
                bump()
                word_start = False
                continue
            bump()
            if char == '"':
                in_double = False
                word_start = False
            elif char == "\n":
                word_start = True
            else:
                word_start = False
            continue
        if char == "\\" and index + 1 < limit:
            bump()
            bump()
            word_start = False
            continue
        if char == "'":
            in_single = True
            word_start = False
            bump()
            continue
        if char == '"':
            in_double = True
            word_start = False
            bump()
            continue
        if char == "$" and index + 1 < limit and source[index + 1] == "{":
            bump()
            bump()
            param_depth += 1
            word_start = False
            continue
        if char == "}" and param_depth:
            bump()
            param_depth -= 1
            word_start = False
            continue
        if char == "<" and index + 1 < limit and source[index + 1] == "<" and param_depth == 0 and not in_single and not in_double:
            mark = HEREDOC_MARK.match(source[index:])
            if mark:
                term = mark.group(2)
                strip_tabs = source[index:index + 3] == "<<-"
                while index < limit and source[index] != "\n":
                    bump()
                if index < limit and source[index] == "\n":
                    bump()
                while index < limit:
                    start = index
                    while index < limit and source[index] != "\n":
                        index += 1
                    body = source[start:index]
                    ending = body.lstrip("\t") if strip_tabs else body
                    if index < limit and source[index] == "\n":
                        index += 1
                        line += 1
                        col = 1
                    else:
                        line += body.count("\n")
                    if ending.strip() == term:
                        break
                word_start = True
                continue
        if char == "#" and word_start and param_depth == 0:
            start_line, start_col = line, col
            chars: list[str] = []
            while index < limit and source[index] != "\n":
                chars.append(bump())
            text = "".join(chars).strip()
            if not _allowed_hash_comment(text, start_line):
                found.append(f"{rel}:{start_line}:{start_col}: {text}")
            word_start = True
            continue
        if char in " \t\r\f\n;|&()<>":
            bump()
            word_start = True
            continue
        bump()
        word_start = False
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail on comments in Python, JS/TS, and shell.")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    found = problems(root)
    if found:
        print(f"{len(found)} comment(s)")
        for item in found:
            print(f" {item}")
        return 1
    print("comments ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
