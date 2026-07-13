from __future__ import annotations

import asyncio
import sys
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
from xinyu_bridge_pre_model_state import InitialSemanticFastState, PreModelPhaseState, PreModelRouteResult
from xinyu_bridge_route_observer import TurnRouteObserver
from xinyu_bridge_turn_pipeline_facade import bind_turn_pipeline_facade as _bind_turn_pipeline_facade
from xinyu_bridge_turn_state import ChatTurnStartState
from xinyu_dialogue_curiosity import evaluate_previous_reaction
from xinyu_memory_event_sourcing import record_chat_event
from xinyu_private_thought_events import record_private_thought_outcome
from xinyu_runtime_presence import record_turn_finished, record_turn_started
from xinyu_runtime_security import source_file_digest
from xinyu_sent_reply_index import visible_text_hash
from xinyu_tinykernel_shadow import record_tinykernel_shadow, shadow_enabled
from xinyu_turn_coherence import finish_turn_coherence
from xinyu_uncertainty_pause import mark_uncertainty_pause_replied


TraceRouteStage = Callable[..., Any]
PreModelRouteRunner = Callable[..., Awaitable[PreModelRouteResult]]
_HOOKS = sys.modules[__name__]


globals().update(_bind_turn_pipeline_facade(_HOOKS))

__all__ = (
    "Any",
    "Awaitable",
    "Callable",
    "ChatTurnStartState",
    "InitialSemanticFastState",
    "PreModelPhaseState",
    "PreModelRouteResult",
    "PreModelRouteRunner",
    "TraceRouteStage",
    "TurnRouteObserver",
    "_HOOKS",
    "_bind_turn_pipeline_facade",
    "_memory_snapshot",
    "annotations",
    "asyncio",
    "datetime",
    "evaluate_previous_reaction",
    "finish_turn_coherence",
    "mark_uncertainty_pause_replied",
    "record_chat_event",
    "record_private_thought_outcome",
    "record_tinykernel_shadow",
    "record_turn_finished",
    "record_turn_started",
    "shadow_enabled",
    "source_file_digest",
    "sys",
    "time",
    "visible_text_hash",
)
