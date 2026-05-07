"""
Custom Textual widgets for the XinYu Runtime TUI.

Gemstone color palette:
  iolite:     #5A4FCF  (primary, tools)
  taaffeite:  #A57EAE  (sub-agents)
  aquamarine: #4C9989  (success, done)
  amber:      #D4920A  (running, warning)
  sapphire:   #0F52BA  (info)
  coral:      #E74C3C  (error)
"""

from xinyu_runtime.builtins.tui.widgets.blocks import (
    CompactSummaryBlock,
    SubAgentBlock,
    ToolBlock,
)
from xinyu_runtime.builtins.tui.widgets.input import ChatInput
from xinyu_runtime.builtins.tui.widgets.messages import (
    QueuedMessage,
    StreamingText,
    SystemNotice,
    TriggerMessage,
    UserMessage,
)
from xinyu_runtime.builtins.tui.widgets.modals import ConfirmModal, SelectionModal
from xinyu_runtime.builtins.tui.widgets.panels import (
    LoadOlderButton,
    RunningPanel,
    ScratchpadPanel,
    SessionInfoPanel,
    TerrariumPanel,
)

__all__ = [
    "ChatInput",
    "CompactSummaryBlock",
    "ConfirmModal",
    "LoadOlderButton",
    "QueuedMessage",
    "RunningPanel",
    "ScratchpadPanel",
    "SelectionModal",
    "SessionInfoPanel",
    "StreamingText",
    "SubAgentBlock",
    "SystemNotice",
    "TerrariumPanel",
    "ToolBlock",
    "TriggerMessage",
    "UserMessage",
]

