"""Tests for MCP resource registrations."""

from __future__ import annotations

import main
from main import kindred_guide


def test_kindred_guide_loads_non_empty_markdown() -> None:
    content = kindred_guide()
    assert content.strip(), "kindred://guide returned empty content"
    assert "journaling" in content.lower()


def test_kindred_guide_file_exists_at_resolved_path() -> None:
    guide_path = main.PROMPTS_DIR / "kindred-guide.md"
    assert guide_path.is_file(), f"expected guide at {guide_path}"
