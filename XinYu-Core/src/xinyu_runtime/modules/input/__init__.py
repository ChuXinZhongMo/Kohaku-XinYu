"""
Input module - receive external input and produce TriggerEvents.

Base classes and protocols are defined here.
Implementations are in xinyu_runtime.builtins.inputs.

Exports:
- InputModule: Protocol for input modules
- BaseInputModule: Base class for input modules
"""

from xinyu_runtime.modules.input.base import BaseInputModule, InputModule

__all__ = [
    # Protocol and base
    "InputModule",
    "BaseInputModule",
]

