"""
Built-in tool implementations.

All tools use the @register_builtin decorator for automatic registration.
This module imports all tool classes to trigger their registration, and
re-exports public API from tool_catalog for convenience.

Internal code should import from ``builtins.tool_catalog`` directly to
avoid pulling in all tool modules.
"""

from xinyu_runtime.builtins.tool_catalog import (
    get_builtin_tool,
    is_builtin_tool,
    list_builtin_tools,
    register_builtin,
)

# Import tools to trigger registration via @register_builtin decorator
from xinyu_runtime.builtins.tools.ask_user import AskUserTool
from xinyu_runtime.builtins.tools.bash import BashTool, PythonTool
from xinyu_runtime.builtins.tools.edit import EditTool
from xinyu_runtime.builtins.tools.glob import GlobTool
from xinyu_runtime.builtins.tools.grep import GrepTool
from xinyu_runtime.builtins.tools.image_gen import ImageGenTool
from xinyu_runtime.builtins.tools.info import InfoTool
from xinyu_runtime.builtins.tools.json_read import JsonReadTool
from xinyu_runtime.builtins.tools.json_write import JsonWriteTool
from xinyu_runtime.builtins.tools.multi_edit import MultiEditTool
from xinyu_runtime.builtins.tools.read import ReadTool
from xinyu_runtime.builtins.tools.scratchpad_tool import ScratchpadTool
from xinyu_runtime.builtins.tools.search_memory import SearchMemoryTool
from xinyu_runtime.builtins.tools.send_message import SendMessageTool
from xinyu_runtime.builtins.tools.skill import SkillTool
from xinyu_runtime.builtins.tools.stop_task import StopTaskTool
from xinyu_runtime.builtins.tools.tree import TreeTool
from xinyu_runtime.builtins.tools.web_fetch import WebFetchTool
from xinyu_runtime.builtins.tools.web_search import WebSearchTool
from xinyu_runtime.builtins.tools.write import WriteTool
from xinyu_runtime.mcp.tools import (
    MCPCallTool,
    MCPConnectTool,
    MCPDisconnectTool,
    MCPListTool,
)

__all__ = [
    # Registry
    "register_builtin",
    "get_builtin_tool",
    "list_builtin_tools",
    "is_builtin_tool",
    # Tools
    "AskUserTool",
    "BashTool",
    "PythonTool",
    "ReadTool",
    "ScratchpadTool",
    "SearchMemoryTool",
    "SendMessageTool",
    "SkillTool",
    "WriteTool",
    "EditTool",
    "GlobTool",
    "MultiEditTool",
    "GrepTool",
    "ImageGenTool",
    "InfoTool",
    "JsonReadTool",
    "JsonWriteTool",
    "StopTaskTool",
    "TreeTool",
    "WebFetchTool",
    "WebSearchTool",
    # MCP
    "MCPListTool",
    "MCPCallTool",
    "MCPConnectTool",
    "MCPDisconnectTool",
]
