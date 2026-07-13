"""Agent Composition Algebra — Pythonic operators for combining agents.

Usage::

    from xinyu_runtime.compose import agent, factory, Pure

    # Persistent agent (reused across calls)
    async with await agent("@kt-biome/creatures/swe") as swe:
        result = await (swe >> extract_code >> reviewer)(task)

    # Ephemeral agent (fresh per call)
    specialist = factory(make_config("coder"))
    result = await specialist("implement this feature")

    # Operators: >> (sequence), & (parallel), | (fallback), * (retry)
    pipeline = (expert * 2) | generalist
    results = await (analyst & writer & designer)(task)

    # Iterate (loop with native control flow)
    async for result in (writer >> reviewer).iterate(task):
        if "APPROVED" in result:
            break
"""

from xinyu_runtime.compose.agent import AgentFactory, AgentRunnable, agent, factory
from xinyu_runtime.compose.core import (
    BaseRunnable,
    FailsWhen,
    Fallback,
    PipelineIterator,
    Product,
    Pure,
    Retry,
    Router,
    Runnable,
    Sequence,
)
from xinyu_runtime.compose.effects import Effects

__all__ = [
    "AgentFactory",
    "AgentRunnable",
    "BaseRunnable",
    "Effects",
    "FailsWhen",
    "Fallback",
    "PipelineIterator",
    "Product",
    "Pure",
    "Retry",
    "Router",
    "Runnable",
    "Sequence",
    "agent",
    "factory",
]
