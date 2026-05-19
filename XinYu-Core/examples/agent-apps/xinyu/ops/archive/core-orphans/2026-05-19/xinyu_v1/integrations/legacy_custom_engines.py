"""Typed wrapper around legacy custom engine modules."""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class LegacyEngineResult:
    ok: bool
    result: Any = None
    error: str = ""


class LegacyCustomEngineRegistry:
    def __init__(self, custom_dir: Path) -> None:
        self._custom_dir = custom_dir
        if str(custom_dir) not in sys.path:
            sys.path.insert(0, str(custom_dir))

    def call(self, module_name: str, function_name: str, *args: Any, **kwargs: Any) -> LegacyEngineResult:
        try:
            module = importlib.import_module(module_name)
            function = getattr(module, function_name)
            return LegacyEngineResult(ok=True, result=function(*args, **kwargs))
        except Exception as exc:
            return LegacyEngineResult(ok=False, error=str(exc))

