"""Terrarium - multi-agent orchestration runtime."""

from xinyu_runtime.terrarium.api import TerrariumAPI
from xinyu_runtime.terrarium.config import (
    ChannelConfig,
    CreatureConfig,
    TerrariumConfig,
    load_terrarium_config,
)
from xinyu_runtime.terrarium.hotplug import HotPlugMixin
from xinyu_runtime.terrarium.observer import ChannelObserver, ObservedMessage
from xinyu_runtime.terrarium.output_log import LogEntry, OutputLogCapture
from xinyu_runtime.terrarium.runtime import TerrariumRuntime

__all__ = [
    "ChannelConfig",
    "ChannelObserver",
    "CreatureConfig",
    "HotPlugMixin",
    "LogEntry",
    "ObservedMessage",
    "OutputLogCapture",
    "TerrariumAPI",
    "TerrariumConfig",
    "TerrariumRuntime",
    "load_terrarium_config",
]
