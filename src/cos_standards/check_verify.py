from __future__ import annotations

import argparse
import html
import json
import re
import shlex
import sys
from pathlib import Path

import yaml

from cos_standards.check_rules import is_package_repo

SKILL_ROOT = Path(".cursor") / "skills"
SLUG = re.compile(r"verify-[a-z0-9]+(?:-[a-z0-9]+)*\Z")
H2 = re.compile(r"^##(?!#)\s+(.+?)\s*#*\s*$")
BRACKET = re.compile(
    r"<\s*([^<>\n]{1,120}?)\s*/?>"
    r"|\{\{\s*([^{}\n]{1,120}?)\s*\}\}"
    r"|\{\s*([^{}\n]{1,120}?)\s*\}"
    r"|＜\s*([^＜＞\n]{1,120}?)\s*＞"
    r"|｛\s*([^｛｝\n]{1,120}?)\s*｝",
    re.IGNORECASE,
)
FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
INLINE = re.compile(r"`([^`\n]+)`")
SLOT_NAMES = {
    "app",
    "command",
    "evidence",
    "evidence-dir",
    "feature",
    "fixme",
    "harness",
    "host",
    "insert",
    "name",
    "password",
    "path",
    "placeholder",
    "port",
    "ready-line",
    "script",
    "slot",
    "surface",
    "tbd",
    "todo",
    "token",
    "user",
    "xxx",
}
QUOTED = re.compile(r"`([^`\n]+)`")
MAKE_NAME = re.compile(r"[A-Za-z0-9_-]+\Z")
SHELL_SPLIT = re.compile(r"[\n;&|<>`]|\$\(")
ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u180e\u200e\u200f"))
REMOVE = re.compile(
    r"\b(?:rm(?:dir)?|(?:delet|remov|wip|eras|purg)\w*|clean(?:s|ed|ing)?)\b",
    re.IGNORECASE,
)
FILLER = re.compile(
    r"\b(?:not yet implemented|not implemented|fill(?: this)?(?: in)? later|coming soon|see the script|to be written|write this(?: section)? later|needs writing|lorem ipsum|placeholder)\b"
)
FILLER_WORD_CAP = 8
FILLER_STOP = {
    "a",
    "be",
    "goes",
    "here",
    "in",
    "is",
    "later",
    "please",
    "section",
    "soon",
    "still",
    "text",
    "the",
    "this",
    "to",
    "write",
    "yet",
}
NEGATED = re.compile(
    r"(?:must\s+not(?:\s+ever)?|do\s+not(?:\s+ever)?|don'?t(?:\s+ever)?|never(?:\s+ever)?)\s+[`'\"]*\s*$",
    re.IGNORECASE,
)
EVIDENCE_PHRASE = re.compile(
    r"\b(?:the\s+proof(?:\s+(?:directory|dir|path))?|proof\s+(?:directory|dir|path)|evidence\s+(?:directory|dir|path))\b",
    re.IGNORECASE,
)
PLACEHOLDER_WORDS = {"tbd", "todo", "fixme", "placeholder", "wip", "ok", "na", "xxx"}
SCRIPT_EXT = re.compile(r"\.(?:py|pyw|sh|bash|zsh|js|mjs|cjs|ts|tsx|rb|pl|ps1)$", re.IGNORECASE)
MIN_WORDS = 3
SURFACES = re.compile(
    r"\b(?:cli|shell|terminal|tui|web|ui|gui|browser|api|http|workbook|vault|markdown|desktop|script|scripts|excel)\b",
    re.IGNORECASE,
)
MIN_DESCRIPTION = 20
SECTIONS = ("Launch", "Doctor", "Drive", "Evidence", "Cleanup", "Helpers")
FEATURE_H2 = ("Sub-features", "How to get to it (user POV)", "Gotchas")
DRIVING = re.compile(r"Driving it with \S.*\S\Z|Driving it with \S\Z")
INTERPRETERS = {"python", "python3", "bash", "sh", "node"}
HELPER_SUFFIXES = {".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts", ".tsx"}
MISSING = "no verify skill at .cursor/skills/verify-<name>/SKILL.md"


def problems(root: Path) -> list[str]:
    if is_package_repo(root):
        return []
    return skill_problems(root)


def skill_problems(root: Path) -> list[str]:
    root = root.resolve()
    base = root / SKILL_ROOT
    if not base.is_dir():
        return [MISSING]
    skills = sorted(path for path in base.iterdir() if path.is_dir() and path.name.startswith("verify-"))
    if not skills:
        return [MISSING]
    found: list[str] = []
    for skill in skills:
        found.extend(_skill(root, skill))
    return found


def _skill(root: Path, skill: Path) -> list[str]:
    prefix = skill.relative_to(root).as_posix()
    out: list[str] = []
    if not SLUG.fullmatch(skill.name):
        out.append(f"{prefix}: directory name must match verify-<name>")
    skill_file = skill / "SKILL.md"
    if not skill_file.is_file():
        out.append(f"{prefix}: missing SKILL.md")
        return out
    try:
        text = skill_file.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{prefix}/SKILL.md: {exc}"]
    data, body, error = _frontmatter(text)
    rel = f"{prefix}/SKILL.md"
    command = ""
    if error:
        out.append(f"{rel}: {error}")
    else:
        command = _meta(out, rel, skill.name, data, root)
    sections = _h2(body)
    titles = [title for title, _ in sections]
    _section_problems(out, rel, titles, sections)
    bodies = {title: text for title, text in sections}
    if command and "Helpers" in bodies and not _shows_command(bodies["Helpers"], command):
        out.append(f"{rel}: Helpers must show the verify command")
    if "Evidence" in bodies and "Cleanup" in bodies:
        _evidence(out, rel, bodies["Evidence"], bodies["Cleanup"])
    out.extend(_slots(rel, text))
    out.extend(_features(root, skill))
    out.extend(_helpers(root, skill, text))
    return out


def _meta(out: list[str], rel: str, dirname: str, data: dict, root: Path) -> str:
    name = data.get("name")
    if name != dirname:
        out.append(f"{rel}: name must be {dirname}")
    description_problem = _description_problem(data.get("description"))
    if description_problem:
        out.append(f"{rel}: {description_problem}")
    command = data.get("verify")
    if not isinstance(command, str) or not command.strip():
        out.append(f"{rel}: verify command is missing")
        return ""
    command = command.strip()
    reason = command_problem(root, command)
    if reason:
        out.append(f"{rel}: {reason}")
    return command


def _frontmatter(text: str) -> tuple[dict, str, str | None]:
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}, text, "missing frontmatter"
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text, "frontmatter does not close"
    raw = text[4:end]
    body = text[end + 5 :]
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return {}, body, f"frontmatter: {exc}"
    if not isinstance(data, dict):
        return {}, body, "frontmatter must be a mapping"
    return data, body, None


def _h2(body: str) -> list[tuple[str, str]]:
    lines = body.splitlines()
    marks: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = H2.match(line)
        if match:
            marks.append((index, match.group(1).strip()))
    sections: list[tuple[str, str]] = []
    for number, (index, title) in enumerate(marks):
        end = marks[number + 1][0] if number + 1 < len(marks) else len(lines)
        sections.append((title, "\n".join(lines[index + 1 : end]).strip()))
    return sections


def _section_problems(out: list[str], rel: str, titles: list[str], sections: list[tuple[str, str]]) -> None:
    positions: list[int] = []
    for name in SECTIONS:
        count = titles.count(name)
        if count == 0:
            out.append(f"{rel}: missing section {name}")
        elif count > 1:
            out.append(f"{rel}: repeated section {name}")
        else:
            positions.append(titles.index(name))
    if len(positions) == len(SECTIONS) and positions != sorted(positions):
        out.append(f"{rel}: sections out of order")
    for title, text in sections:
        if title not in SECTIONS:
            continue
        if not text:
            out.append(f"{rel}: empty section {title}")
        elif not _meaningful(text):
            out.append(f"{rel}: section {title} is only a placeholder")


def _description_problem(description: object) -> str | None:
    if not isinstance(description, str) or not description.strip():
        return "description is empty"
    text = description.strip()
    if len(text) < MIN_DESCRIPTION:
        return "description is too short"
    if not SURFACES.search(text):
        return "description must name the surface"
    return None


def _plain_phrase(text: str) -> str:
    cleaned = html.unescape(text)
    cleaned = re.sub(r"<!--.*?-->", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<!--.*", " ", cleaned, flags=re.DOTALL)
    cleaned = cleaned.translate(ZERO_WIDTH)
    cleaned = cleaned.replace("`", " ")
    cleaned = re.sub(r"[^A-Za-z0-9']+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip().lower()


def _meaningful(text: str) -> bool:
    phrase = _plain_phrase(text)
    if not phrase:
        return False
    words = phrase.split()
    if _filler_only(words):
        return False
    words = _collapse_todo(words)
    if words and all(len(word) == 1 for word in words):
        words = ["".join(words)]
    words = [word for word in words if word not in PLACEHOLDER_WORDS]
    return len(words) >= MIN_WORDS


def _filler_only(words: list[str]) -> bool:
    if len(words) >= FILLER_WORD_CAP:
        return False
    phrase = " ".join(words)
    spans = [(match.start(), match.end()) for match in FILLER.finditer(phrase)]
    if not spans:
        return False
    cursor = 0
    for word in words:
        start = phrase.find(word, cursor)
        end = start + len(word)
        cursor = end + 1
        inside = any(start >= span_start and end <= span_end for span_start, span_end in spans)
        if not inside and word not in FILLER_STOP:
            return False
    return True


def _collapse_todo(words: list[str]) -> list[str]:
    folded: list[str] = []
    index = 0
    while index < len(words):
        if words[index] == "to" and index + 1 < len(words) and words[index + 1] == "do":
            folded.append("todo")
            index += 2
            continue
        folded.append(words[index])
        index += 1
    return folded


def _evidence(out: list[str], rel: str, evidence: str, cleanup: str) -> None:
    left = _evidence_paths(evidence)
    right = _evidence_paths(cleanup)
    if not any(_covers(a, b) for a in left for b in right):
        out.append(f"{rel}: Evidence and Cleanup must quote the same evidence/ path")
    paths = left | right
    if not _cleanup_keeps(cleanup, paths):
        out.append(f"{rel}: Cleanup must say do not delete the evidence path")
    if _cleanup_removes(cleanup, paths):
        out.append(f"{rel}: Cleanup removes the evidence path")


def _clauses(text: str) -> list[str]:
    flat = re.sub(r"\s*\n\s*", " ", text)
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", flat) if part.strip()]


def _mentions_path(text: str, path: str) -> bool:
    return re.search(r"(?<![\w.-])(?:\./)?" + re.escape(path) + r"/?(?![\w-])", text) is not None


def _mentions_evidence(clause: str, paths: set[str]) -> bool:
    folded = clause.replace("`", "")
    if EVIDENCE_PHRASE.search(folded):
        return True
    if re.search(r"(?<![\w.-])(?:\./)?evidence/\S*[*?\[]", folded, re.IGNORECASE):
        return True
    if any(_mentions_path(folded, path) for path in paths):
        return True
    return _glob_covers(folded, paths)


def _glob_covers(text: str, paths: set[str]) -> bool:
    for token in re.findall(r"\S+", text):
        token = token.strip("`.,;:\"'")
        if token.startswith("./"):
            token = token[2:]
        if not token.startswith("evidence/") or not any(mark in token for mark in "*?["):
            continue
        prefix = re.split(r"[*?\[\]]", token, maxsplit=1)[0].rstrip("/")
        for path in paths:
            if path == prefix or path.startswith(prefix + "/"):
                return True
    return False


def _unnegated_removal(clause: str) -> bool:
    for match in REMOVE.finditer(clause):
        before = clause[max(0, match.start() - 40) : match.start()]
        if not NEGATED.search(before):
            return True
    return False


def _negated_removal(clause: str) -> bool:
    for match in REMOVE.finditer(clause):
        before = clause[max(0, match.start() - 40) : match.start()]
        if NEGATED.search(before):
            return True
    return False


def _cleanup_keeps(cleanup: str, paths: set[str]) -> bool:
    return any(_mentions_evidence(clause, paths) and _negated_removal(clause) for clause in _clauses(cleanup))


def _cleanup_removes(cleanup: str, paths: set[str]) -> bool:
    return any(_mentions_evidence(clause, paths) and _unnegated_removal(clause) for clause in _clauses(cleanup))


def _evidence_paths(text: str) -> set[str]:
    found: set[str] = set()
    for match in QUOTED.finditer(text):
        token = match.group(1).strip().rstrip("/")
        if token.startswith("./"):
            token = token[2:]
        if not token.startswith("evidence/"):
            continue
        parts = token.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            continue
        found.add(token)
    return found


def _covers(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def _slots(rel: str, text: str, *, source: bool = False) -> list[str]:
    raw = html.unescape(text)
    found = _source_slots(raw) if source else _markdown_slots(raw)
    return [f"{rel}: template slot {slot} is still present" for slot in sorted(set(found))]


def _markdown_slots(text: str) -> list[str]:
    code: list[str] = []

    def take_fence(match: re.Match[str]) -> str:
        code.append(match.group(1))
        return "\n"

    def take_inline(match: re.Match[str]) -> str:
        code.append(match.group(1))
        return " "

    prose = INLINE.sub(take_inline, FENCE.sub(take_fence, text))
    return _placeholder_hits(prose) + _placeholder_hits("\n".join(code))


def _source_slots(text: str) -> list[str]:
    return _placeholder_hits(text)


def _placeholder_hits(text: str) -> list[str]:
    hits: list[str] = []
    for match in BRACKET.finditer(text):
        inner = next(group for group in match.groups() if group is not None)
        if _is_placeholder(inner):
            hits.append(match.group(0))
    return hits


def _is_placeholder(inner: str) -> bool:
    token = inner.strip()
    if not token or token.startswith("/"):
        return False
    token = token.strip("/").strip()
    if not token:
        return False
    lowered = token.lower()
    if lowered.startswith(("http://", "https://", "mailto:")):
        return False
    if any(mark in token for mark in ":\"'=,"):
        return False
    compact = re.sub(r"[\s_]+", "-", lowered).strip("-")
    if re.fullmatch(r"\d+", compact):
        return True
    return bool(re.fullmatch(r"[a-z][a-z0-9-]*", compact) and compact in SLOT_NAMES)


def _features(root: Path, skill: Path) -> list[str]:
    prefix = skill.relative_to(root).as_posix()
    features = skill / "features"
    readme = features / "README.md"
    if not readme.is_file():
        return [f"{prefix}: missing features/README.md"]
    out: list[str] = []
    nested = sorted(path for path in features.rglob("*.md") if path.parent != features)
    for path in nested:
        out.append(f"{path.relative_to(root).as_posix()}: feature files live next to features/README.md")
    files = sorted(path for path in features.glob("*.md") if path.name != "README.md")
    if not files:
        out.append(f"{prefix}: feature map has no feature file")
    try:
        index = readme.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{prefix}/features/README.md: {exc}"]
    out.extend(_slots(f"{prefix}/features/README.md", index))
    linked = set(re.findall(r"\]\((?:\./)?([^)/\s]+\.md)\)", index))
    for path in files:
        rel = path.relative_to(root).as_posix()
        if path.name not in linked and f"./{path.name}" not in index:
            out.append(f"{prefix}/features/README.md: does not link {path.name}")
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            out.append(f"{rel}: {exc}")
            continue
        out.extend(_feature(rel, text))
        out.extend(_slots(rel, text))
    for name in sorted(linked):
        if not (features / name).is_file():
            out.append(f"{prefix}/features/README.md: links missing {name}")
    return out


def _feature(rel: str, text: str) -> list[str]:
    sections = _h2(text)
    titles = [title for title, _ in sections]
    out: list[str] = []
    for name in FEATURE_H2:
        if name not in titles:
            out.append(f"{rel}: missing heading {name}")
        else:
            _heading_body(out, rel, name, dict(sections)[name])
    driving = [title for title in titles if title.startswith("Driving it with")]
    if len(driving) != 1 or not DRIVING.fullmatch(driving[0] if driving else ""):
        out.append(f"{rel}: missing heading Driving it with <harness>")
    else:
        _heading_body(out, rel, driving[0], dict(sections)[driving[0]])
    return out


def _heading_body(out: list[str], rel: str, title: str, text: str) -> None:
    if not text:
        out.append(f"{rel}: empty heading {title}")
    elif not _meaningful(text):
        out.append(f"{rel}: heading {title} is only a placeholder")


def _helpers(root: Path, skill: Path, skill_text: str) -> list[str]:
    out: list[str] = []
    for path in sorted(skill.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(skill).parts
        if rel_parts[0] == "features" or path.name == "SKILL.md" and path.parent == skill:
            continue
        rel = path.relative_to(root).as_posix()
        if path.name not in skill_text:
            out.append(f"{rel}: helper is not named in SKILL.md")
        if _script_like(path) and path.stat().st_mode & 0o111 == 0:
            out.append(f"{rel}: helper is not executable")
        try:
            helper_text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        out.extend(_slots(rel, helper_text, source=True))
    return out


def _script_like(path: Path) -> bool:
    if path.suffix.lower() in HELPER_SUFFIXES:
        return True
    try:
        first = path.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, UnicodeDecodeError, IndexError):
        return False
    return first.startswith("#!")


def command_problem(root: Path, command: str) -> str | None:
    if SHELL_SPLIT.search(command):
        return "verify command must be a single command"
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return f"verify command: {exc}"
    if not parts:
        return "verify command is empty"
    if len(parts) >= 3 and parts[0] == "uv" and parts[1] == "run":
        parts = parts[2:]
    if not parts:
        return "verify command is empty"
    tool = parts[0]
    if tool == "make":
        return _make(root, parts)
    if tool in {"npm", "pnpm", "yarn"}:
        return _package_script(root, parts)
    if tool in INTERPRETERS:
        script = _path_token(parts[1:])
        if script is None:
            return "verify command must name a script in the repo"
        return _file(root, script, direct=False)
    if "/" not in tool and not tool.startswith("./"):
        return "verify command must name a script in the repo"
    return _file(root, tool, direct=True)


def _path_token(parts: list[str]) -> str | None:
    for token in parts:
        if token.startswith("-"):
            continue
        if "/" in token or token.startswith("./"):
            return token
    return None


def _make(root: Path, parts: list[str]) -> str | None:
    if any(part.startswith("-") for part in parts[1:]):
        return "verify command: make flags are not supported"
    names = [part for part in parts[1:] if "=" not in part]
    if len(names) != 1 or not MAKE_NAME.fullmatch(names[0]):
        return "verify command: make needs one target"
    target = names[0]
    for filename in ("Makefile", "makefile", "GNUmakefile"):
        path = root / filename
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(rf"(?m)^{re.escape(target)}\s*:", text):
            return _recipe_problem(root, _make_recipe(text, target))
    return f"verify command: make target {target} is not in a Makefile"


def _make_recipe(text: str, target: str) -> str:
    lines = text.splitlines()
    recipe: list[str] = []
    capturing = False
    for line in lines:
        if not capturing:
            match = re.match(rf"^{re.escape(target)}\s*:(.*)$", line)
            if match:
                capturing = True
                if match.group(1).strip():
                    recipe.append(match.group(1).strip())
            continue
        if not line.strip():
            continue
        if line.startswith(("\t", " ")):
            recipe.append(line.strip())
            continue
        break
    return "\n".join(recipe)


def _package_script(root: Path, parts: list[str]) -> str | None:
    tool = parts[0]
    rest = parts[1:]
    if tool == "npm":
        if not rest or rest[0] != "run":
            return "verify command: npm needs npm run <script>"
        rest = rest[1:]
    elif rest and rest[0] == "run":
        rest = rest[1:]
    if not rest or rest[0].startswith("-"):
        return "verify command: package script name is missing"
    name = rest[0]
    path = root / "package.json"
    if not path.is_file():
        return "verify command: package.json is missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return f"verify command: package.json: {exc}"
    scripts = data.get("scripts") if isinstance(data, dict) else None
    if not isinstance(scripts, dict) or not isinstance(scripts.get(name), str) or not scripts[name].strip():
        return f"verify command: package script {name} is missing"
    return _recipe_problem(root, scripts[name])


def _recipe_problem(root: Path, text: str) -> str | None:
    if _is_noop(text):
        return "verify command is a no-op"
    for relative in _recipe_paths(text):
        reason = _file(root, relative, direct=False)
        if reason:
            return reason
    return None


def _is_noop(text: str) -> bool:
    kept = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    if not kept and text.strip() and not text.strip().startswith("#"):
        kept = [text.strip()]
    if not kept:
        return True
    commands: list[list[str]] = []
    for chunk in re.split(r"&&|\|\||[;|\n]", "\n".join(kept)):
        unfolded = re.sub(r"\$\([^)]*\)|\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*", " ", chunk)
        try:
            parts = shlex.split(unfolded)
        except ValueError:
            parts = unfolded.split()
        if parts:
            commands.append(parts)
    if not commands:
        return True
    for parts in commands:
        command = parts[0]
        if command in {"echo", "true", ":"}:
            continue
        if command == "exit" and (len(parts) == 1 or parts[1] == "0"):
            continue
        return False
    return True


def _recipe_paths(text: str) -> list[str]:
    unfolded = re.sub(r"\$\([^)]*\)|\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*", " ", text)
    try:
        parts = shlex.split(unfolded)
    except ValueError:
        parts = unfolded.split()
    found: list[str] = []
    for part in parts:
        if part.startswith(("http://", "https://", "-")):
            continue
        token = part[2:] if part.startswith("./") else part
        if not token or token.startswith(("/", "~")) or ".." in Path(token).parts:
            continue
        if "/" in token or SCRIPT_EXT.search(token):
            found.append(token)
    return found


def _shows_command(helpers: str, command: str) -> bool:
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    paths = [part for part in parts if "/" in part or part.startswith("./")]
    if paths:
        return all(_has_token(helpers, part) for part in paths)
    return _has_token(helpers, command)


def _has_token(text: str, token: str) -> bool:
    forms = {token, token[2:] if token.startswith("./") else f"./{token}"}
    return any(re.search(r"(?<![\w./-])" + re.escape(form) + r"(?![\w./-])", text) for form in forms)


def _file(root: Path, relative: str, *, direct: bool) -> str | None:
    path = _inside(root, relative)
    if path is None:
        return "verify command must name a script in the repo"
    if not path.is_file():
        return f"verify command {relative} does not exist"
    if path.stat().st_size == 0:
        return f"verify command {relative} is empty"
    if not direct:
        return None
    try:
        first = path.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, UnicodeDecodeError, IndexError):
        first = ""
    if not first.startswith("#!"):
        return f"verify command {relative} needs a shebang"
    if path.stat().st_mode & 0o111 == 0:
        return f"verify command {relative} is not executable"
    return None


def _inside(root: Path, relative: str) -> Path | None:
    raw = relative[2:] if relative.startswith("./") else relative
    if not raw or raw.startswith(("/", "~")) or ".." in Path(raw).parts:
        return None
    path = (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when a repo has no runnable verify skill.")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    found = problems(root)
    if found:
        print(f"{len(found)} verify skill problem(s)")
        for item in found:
            print(f" {item}")
        return 1
    print("verify skill ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
