from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_learning import ingest as learning_ingest_bridge
from xinyu_bridge_learning import study as learning_study_bridge
from xinyu_bridge_observation import observe as learning_observe_bridge
from xinyu_recent_attachment_context import record_recent_attachment_context


@dataclass(slots=True)
class LearningService:
    xinyu_dir: Path
    memory_root: Path
    cleanup_idle_sessions: Callable[..., Any]
    session_count: Callable[[], int]
    lock: Any
    load_local_env: Callable[[Path], None]

    async def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = await learning_ingest_bridge(
            xinyu_dir=self.xinyu_dir,
            memory_root=self.memory_root,
            payload=payload,
            cleanup_idle_sessions=self.cleanup_idle_sessions,
            session_count=self.session_count,
            lock=self.lock,
            load_local_env=self.load_local_env,
        )
        self._record_recent_attachment_context(payload, result)
        return result

    async def study(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await learning_study_bridge(
            xinyu_dir=self.xinyu_dir,
            memory_root=self.memory_root,
            payload=payload,
            cleanup_idle_sessions=self.cleanup_idle_sessions,
            session_count=self.session_count,
            lock=self.lock,
            load_local_env=self.load_local_env,
        )

    async def observe(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await learning_observe_bridge(
            xinyu_dir=self.xinyu_dir,
            memory_root=self.memory_root,
            payload=payload,
            cleanup_idle_sessions=self.cleanup_idle_sessions,
            session_count=self.session_count,
            lock=self.lock,
        )

    def _record_recent_attachment_context(self, payload: dict[str, Any], result: dict[str, Any]) -> None:
        try:
            if record_recent_attachment_context(self.xinyu_dir, payload, result):
                notes = result.get("notes")
                if not isinstance(notes, list):
                    notes = []
                    result["notes"] = notes
                notes.append("recent_attachment_context_recorded")
        except Exception as exc:
            notes = result.get("notes")
            if not isinstance(notes, list):
                notes = []
                result["notes"] = notes
            notes.append(f"recent_attachment_context_error:{type(exc).__name__}")


def build_learning_service(
    *,
    xinyu_dir: Path,
    memory_root: Path,
    cleanup_idle_sessions: Callable[..., Any],
    session_count: Callable[[], int],
    lock: Any,
    load_local_env: Callable[[Path], None],
) -> LearningService:
    return LearningService(
        xinyu_dir=xinyu_dir,
        memory_root=memory_root,
        cleanup_idle_sessions=cleanup_idle_sessions,
        session_count=session_count,
        lock=lock,
        load_local_env=load_local_env,
    )
