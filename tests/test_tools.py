"""Tests for the agent tools registry and dispatcher."""

import pytest

from tuya_agent.tools import TOOLS, dispatch


class TestToolsRegistry:
    def test_all_tools_have_required_fields(self):
        for tool in TOOLS:
            assert "name" in tool, f"Tool missing name: {tool}"
            assert "description" in tool, f"Tool {tool['name']} missing description"
            assert "parameters" in tool, f"Tool {tool['name']} missing parameters"
            assert "function" in tool, f"Tool {tool['name']} missing function reference"

    def test_expected_tools_are_registered(self):
        names = {t["name"] for t in TOOLS}
        expected = {
            "list_devices",
            "get_device",
            "get_device_status",
            "get_device_specification",
            "control_device",
            "get_device_event_logs",
            "get_device_report_logs",
            "get_device_statistics",
            "list_scenes",
            "trigger_scene",
            "get_automation",
            "enable_automation",
            "disable_automation",
            "collect_realtime_events",
            "collect_logs",
            "get_collection_status",
        }
        assert expected.issubset(names), f"Missing tools: {expected - names}"

    def test_no_duplicate_tool_names(self):
        names = [t["name"] for t in TOOLS]
        assert len(names) == len(set(names)), "Duplicate tool names found"


class TestDispatch:
    @pytest.mark.asyncio
    async def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            await dispatch(None, "nonexistent_tool", {})  # type: ignore[arg-type]
