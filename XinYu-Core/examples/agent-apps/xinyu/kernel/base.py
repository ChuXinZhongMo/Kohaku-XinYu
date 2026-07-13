"""Base abstractions for the Cognitive Kernel.

This file is intentionally minimal at this stage (K-001).
Future kernel modules (Belief, Prediction, etc.) may inherit or use these.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class KernelModule(ABC):
    """Abstract base for all modules that belong to the Cognitive Kernel."""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize the module state to a dict."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> KernelModule:
        """Reconstruct from serialized dict."""
        raise NotImplementedError
