# NetBrain MCP Server -- Project-Specific Lessons

Review at session start. These are hard constraints learned during this project.

## Architecture

- FastMCP 3.x uses `instructions` not `description` in the constructor. The `description` kwarg was removed and will raise TypeError.
- FastMCP 3.x uses `Context` parameter injection for tools to access lifespan state. Access via `ctx.lifespan_context["key"]`. The old `mcp.dependencies` pattern does not exist.
- FastMCP 3.x requires `list_tools()` (async) to enumerate registered tools. There is no `_tool_manager._tools` internal dict.
- hatchling build-system with `[tool.hatch.build.targets.wheel] packages = ["src/netbrain_mcp"]` is required for uv to install the package as editable and for tests to import it.

## API Quirks

- NetBrain API uses custom status codes (790200=success, 795000=auth fail, 791000=null param, 791006=not found) in the JSON body, not HTTP status codes.
- NetBrain requires setting a "current domain" after login before any data calls work. This is a PUT to /ServicesAPI/API/V1/Session/CurrentDomain.
- Path calculation and diagnosis are async operations that return a taskId. The MCP tools block+poll internally so the LLM never has to manage task IDs.

## Testing

- Server tests must use `@pytest.mark.asyncio` for `list_tools()` since it is async in FastMCP 3.x.
- `pytest-asyncio` with `asyncio_mode = "auto"` in pyproject.toml handles async test discovery.

## Correction Log
Format: YYYY-MM-DD | category | brief description
2026-03-16 | architecture | FastMCP 3.x removed `description` kwarg from constructor. Use `instructions` instead.
2026-03-16 | architecture | FastMCP 3.x context injection uses `Context` param + `ctx.lifespan_context`, not `mcp.dependencies`.
2026-03-16 | build | uv project needs `[build-system]` with hatchling for package to be importable in tests.
