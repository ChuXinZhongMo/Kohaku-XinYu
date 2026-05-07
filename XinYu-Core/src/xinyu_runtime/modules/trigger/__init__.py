"""
Trigger module - automatic event generation.

Triggers produce TriggerEvents without user input:
- TimerTrigger: Fire at intervals
- ContextUpdateTrigger: Fire when context changes
- IdleTrigger: Fire after inactivity (planned)
- CompositeTrigger: Combine multiple triggers (planned)

Usage:
    from xinyu_runtime.modules.trigger import TimerTrigger, ContextUpdateTrigger

    # Timer-based
    timer = TimerTrigger(interval=60, prompt="Check status")
    await timer.start()
    event = await timer.wait_for_trigger()

    # Context-based
    context_trigger = ContextUpdateTrigger(prompt="New context")
    await context_trigger.start()
    context_trigger.set_context({"input": "hello"})
    event = await context_trigger.wait_for_trigger()
"""

from xinyu_runtime.modules.trigger.base import BaseTrigger, TriggerModule
from xinyu_runtime.modules.trigger.channel import ChannelTrigger
from xinyu_runtime.modules.trigger.context import ContextUpdateTrigger
from xinyu_runtime.modules.trigger.timer import TimerTrigger

__all__ = [
    # Protocol and base
    "TriggerModule",
    "BaseTrigger",
    # Implementations
    "ChannelTrigger",
    "ContextUpdateTrigger",
    "TimerTrigger",
]
