"""
TUI (Terminal UI) module - full-screen Textual app for agent interaction.

Provides TUIInput and TUIOutput that share a TUISession (Textual app)
via the Session registry. Both modules access session.tui for shared state.

Features:
- Split-pane layout: output (left) + status tabs (right)
- Tabbed side panel: Status, Logs
- Input prompt with line editing
- Mouse support
- Rich markup in output
"""

from kohakuterrarium.builtins.tui.session import TUISession

__all__ = ["TUISession"]
