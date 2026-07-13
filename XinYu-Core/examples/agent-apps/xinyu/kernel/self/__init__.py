"""Self subpackage - the core persistent subject of the Cognitive Kernel."""

from .model import OwnedObject, SelfModel
from .ownership import Self
from .persistence import (
    load_self_from_json,
    save_self_to_json,
    self_from_json_string,
    self_to_json_string,
)

__all__ = [
    "OwnedObject",
    "Self",
    "SelfModel",
    "load_self_from_json",
    "save_self_to_json",
    "self_from_json_string",
    "self_to_json_string",
]
