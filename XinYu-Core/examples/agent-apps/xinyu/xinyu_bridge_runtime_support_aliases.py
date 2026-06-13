from __future__ import annotations

from pathlib import Path
from typing import Any

from xinyu_bridge_runtime_action_aliases import install_action_aliases
from xinyu_bridge_runtime_reply_aliases import install_reply_renderer_aliases
from xinyu_bridge_runtime_session_aliases import install_session_turn_aliases
from xinyu_bridge_runtime_state_aliases import install_state_aliases


def install_runtime_support_aliases(
    runtime_cls: type[Any],
    *,
    bridge_source_path: Path,
) -> type[Any]:
    install_state_aliases(runtime_cls)
    install_action_aliases(runtime_cls)
    install_session_turn_aliases(runtime_cls)
    install_reply_renderer_aliases(runtime_cls, bridge_source_path=bridge_source_path)
    return runtime_cls
