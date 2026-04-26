"""
Input module - receive external input and produce TriggerEvents.

Base classes and protocols are defined here.
Implementations are in kohakuterrarium.builtins.inputs.

Exports:
- InputModule: Protocol for input modules
- BaseInputModule: Base class for input modules
"""

from kohakuterrarium.modules.input.base import BaseInputModule, InputModule

__all__ = [
    # Protocol and base
    "InputModule",
    "BaseInputModule",
]
