from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from typing import Any


class DataclassMappingState:
    def as_dict(self) -> dict[str, Any]:
        return {item.name: getattr(self, item.name) for item in fields(self)}

    def __getitem__(self, key: str) -> Any:
        if key not in self:
            raise KeyError(key)
        return getattr(self, key)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and any(item.name == key for item in fields(self))

    def __len__(self) -> int:
        return len(fields(self))

    def keys(self) -> list[str]:
        return [item.name for item in fields(self)]

    def items(self) -> list[tuple[str, Any]]:
        return [(key, getattr(self, key)) for key in self.keys()]

    def values(self) -> list[Any]:
        return [value for _, value in self.items()]

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default) if key in self else default

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DataclassMappingState):
            return self.as_dict() == other.as_dict()
        if isinstance(other, Mapping):
            return self.as_dict() == dict(other)
        return NotImplemented
