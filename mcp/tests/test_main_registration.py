"""Tests for MCP server registration: kindred://guide resource, tool descriptions, annotations."""

from __future__ import annotations

from main import mcp

GUIDE_URI = "kindred://guide"

READ_ONLY_TOOLS = {
    "get_entry",
    "list_recent_entries",
    "search_entries",
    "list_patterns",
    "get_pattern",
    "list_occurrences",
}

WRITE_TOOLS = {"save_entry", "log_occurrence"}

TOOL_HINTS = {
    "save_entry": "confirm the summary",
    "list_patterns": "recurring experience",
    "log_occurrence": "Never initiate HCB unprompted",
    "list_recent_entries": "surface past entries",
    "search_entries": "surface past entries",
}


async def test_kindred_guide_resource_registered() -> None:
    resources = await mcp.list_resources()
    matching = [r for r in resources if str(r.uri) == GUIDE_URI]
    assert len(matching) == 1
    resource = matching[0]
    assert resource.mimeType == "text/markdown"
    assert resource.name == "Kindred Guide"
    # Explicit description= is required (not docstring fallback) per FastMCP gotcha.
    assert resource.description is not None
    assert "Behavioural guide" in resource.description


async def test_kindred_guide_resource_readable() -> None:
    contents = list(await mcp.read_resource(GUIDE_URI))
    assert len(contents) == 1
    body = contents[0].content
    assert isinstance(body, str)
    assert body.strip()
    assert "Kindred" in body
    assert "Hot Cross Bun" in body
    for section in ("## Stance", "## Opening a session", "## Closing a session", "## Tools"):
        assert section in body, f"Guide missing section header: {section}"
    registered_tools = {t.name for t in await mcp.list_tools()}
    for tool_name in registered_tools:
        assert tool_name in body, f"Guide missing reference to tool: {tool_name}"


async def test_old_prompts_unregistered() -> None:
    prompts = await mcp.list_prompts()
    names = {p.name for p in prompts}
    assert "kindred_start" not in names
    assert "kindred_hcb" not in names
    assert "kindred_close" not in names


async def test_tool_descriptions_contain_guide_nudge() -> None:
    tools = await mcp.list_tools()
    assert {t.name for t in tools} == READ_ONLY_TOOLS | WRITE_TOOLS
    for tool in tools:
        assert tool.description is not None, f"{tool.name} has no description"
        assert GUIDE_URI in tool.description, f"{tool.name} description missing guide nudge"


async def test_tool_specific_hints() -> None:
    tools = {t.name: t for t in await mcp.list_tools()}
    for name, hint in TOOL_HINTS.items():
        description = tools[name].description
        assert description is not None
        assert hint in description, f"{name} description missing {hint!r}"


async def test_read_only_tools_annotated() -> None:
    tools = {t.name: t for t in await mcp.list_tools()}
    for name in READ_ONLY_TOOLS:
        annotations = tools[name].annotations
        assert annotations is not None, f"{name} has no annotations"
        assert annotations.readOnlyHint is True, f"{name} not marked readOnlyHint=True"


async def test_write_tools_not_marked_readonly() -> None:
    tools = {t.name: t for t in await mcp.list_tools()}
    for name in WRITE_TOOLS:
        annotations = tools[name].annotations
        if annotations is not None:
            assert annotations.readOnlyHint is not True, f"{name} incorrectly marked read-only"
