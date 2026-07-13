"""Exceptions for the Cognitive Kernel."""

from __future__ import annotations


class KernelError(Exception):
    """Base exception for all kernel-related errors."""


class OwnershipError(KernelError):
    """Raised when ownership operations fail (e.g. claiming already owned object)."""
