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
            # Device tools
            "list_devices",
            "get_device",
            "get_device_status",
            "get_device_specification",
            "get_device_functions",
            "get_sub_devices",
            "control_device",
            # Logging tools
            "get_device_event_logs",
            "get_device_report_logs",
            "get_device_statistics",
            # Scene tools
            "list_scenes",
            "trigger_scene",
            # Real-time event tools
            "collect_realtime_events",
            "watch_realtime_events",
            # Log collector tools
            "collect_logs",
            "get_collection_status",
            "query_logs",
            "get_collection_runs",
            # Space tools
            "resolve_space",
            "list_spaces",
            # Timer tools
            "list_device_timers",
            "add_device_timer",
            "toggle_device_timer",
            # Weather tools
            "get_weather_forecast",
            "get_weather_by_location",
            # Lock tools
            "unlock_door",
            "remote_unlock_door",
            # IR control tools
            "list_ir_remotes",
            "get_ir_remote_keys",
            "send_ir_command",
            # Location tools
            "get_device_location",
            # Firmware tools
            "get_firmware_info",
            # Group tools
            "list_device_groups",
            "get_device_group",
            # Scene template tools
            "list_scene_templates",
            # Notification tools
            "send_notification",
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
