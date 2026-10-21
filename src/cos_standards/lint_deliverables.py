"""Deliverable lint. Warnings fail. There is no switch to turn that off."""

from __future__ import annotations

from cos_standards.lint_writing import Hit, apply_strict, lint_text


def lint_deliverable_text(text: str, name: str, rules: list[dict]) -> list[Hit]:
    """Lint one deliverable. Every warning is returned as an error."""
    return apply_strict(lint_text(text, name, rules), strict=True)
