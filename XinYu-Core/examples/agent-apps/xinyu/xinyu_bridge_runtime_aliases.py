from __future__ import annotations

from pathlib import Path
from typing import Any

import xinyu_bridge_runtime_codex_aliases
import xinyu_bridge_runtime_desktop_aliases
import xinyu_bridge_runtime_dialogue_aliases
import xinyu_bridge_runtime_life_aliases
import xinyu_bridge_runtime_route_aliases
import xinyu_bridge_runtime_support_aliases


def install_runtime_aliases(runtime_cls: type[Any], *, bridge_source_path: Path) -> type[Any]:
    xinyu_bridge_runtime_codex_aliases.install_runtime_codex_aliases(runtime_cls)
    xinyu_bridge_runtime_support_aliases.install_runtime_support_aliases(
        runtime_cls,
        bridge_source_path=bridge_source_path,
    )
    xinyu_bridge_runtime_dialogue_aliases.install_runtime_dialogue_aliases(runtime_cls)
    xinyu_bridge_runtime_life_aliases.install_runtime_life_aliases(runtime_cls)
    xinyu_bridge_runtime_desktop_aliases.install_runtime_desktop_aliases(runtime_cls)
    xinyu_bridge_runtime_route_aliases.install_runtime_route_aliases(runtime_cls)
    return runtime_cls
