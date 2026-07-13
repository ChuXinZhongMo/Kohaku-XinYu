"""
Builtin tool registry (backward-compatible re-exports).

All real logic now lives in ``builtins.tool_catalog``. This module
re-exports the public API so that existing tool modules importing
``from xinyu_runtime.builtins.tools.registry import register_builtin``
continue to work without changes.
"""

from xinyu_runtime.builtins.tool_catalog import (
    get_builtin_tool,
    is_builtin_tool,
    list_builtin_tools,
    register_builtin,
)

__all__ = [
    "get_builtin_tool",
    "is_builtin_tool",
    "list_builtin_tools",
    "register_builtin",
]
