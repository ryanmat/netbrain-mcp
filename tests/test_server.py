# Description: Integration test stubs for the NetBrain MCP server.
# Description: Validates server instantiation and tool registration.
from __future__ import annotations

import pytest

from netbrain_mcp.server import mcp


class TestServerSetup:
    def test_server_name(self) -> None:
        assert mcp.name == "NetBrain MCP Server"

    @pytest.mark.asyncio
    async def test_tools_registered(self) -> None:
        tools = await mcp.list_tools()
        tool_names = {t.name for t in tools}
        expected = {
            "get_devices",
            "get_device_attributes",
            "get_device_config",
            "get_neighbors",
            "calculate_path",
            "trigger_diagnosis",
            "get_events",
            "get_change_analysis",
            "search_devices",
        }
        assert expected == tool_names, f"Missing tools: {expected - tool_names}"

    @pytest.mark.asyncio
    async def test_tool_count(self) -> None:
        tools = await mcp.list_tools()
        assert len(tools) == 9
