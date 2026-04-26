"""Verify all 9 terrarium tools register correctly after the split."""

from kohakuterrarium.builtins.tool_catalog import get_builtin_tool
from kohakuterrarium.terrarium.tool_registration import (
    ensure_terrarium_tools_registered,
)


def test_all_terrarium_tools_registered():
    ensure_terrarium_tools_registered()
    expected_tools = [
        "terrarium_create",
        "terrarium_status",
        "terrarium_stop",
        "terrarium_send",
        "terrarium_observe",
        "terrarium_history",
        "creature_start",
        "creature_stop",
        "creature_interrupt",
    ]
    for tool_name in expected_tools:
        tool_cls = get_builtin_tool(tool_name)
        assert tool_cls is not None, f"Tool '{tool_name}' not registered"
