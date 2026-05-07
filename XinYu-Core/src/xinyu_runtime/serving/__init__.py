"""Core service API for hosting and managing agents and terrariums.

All runtime operations go through XinYuManager. Event types are
transport-agnostic dataclasses usable by any interface layer.
"""

from xinyu_runtime.serving.agent_session import AgentSession
from xinyu_runtime.serving.events import ChannelEvent, OutputEvent
from xinyu_runtime.serving.manager import XinYuManager

__all__ = [
    "AgentSession",
    "ChannelEvent",
    "OutputEvent",
    "XinYuManager",
]
