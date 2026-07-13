"""
Reusable test infrastructure for XinYu Runtime.

Provides fake/mock primitives for testing the agent framework without real LLMs.
"""

from xinyu_runtime.testing.agent import TestAgentBuilder
from xinyu_runtime.testing.events import EventRecorder, RecordedEvent
from xinyu_runtime.testing.llm import ScriptedLLM, ScriptEntry
from xinyu_runtime.testing.output import OutputRecorder

__all__ = [
    "EventRecorder",
    "OutputRecorder",
    "RecordedEvent",
    "ScriptEntry",
    "ScriptedLLM",
    "TestAgentBuilder",
]

