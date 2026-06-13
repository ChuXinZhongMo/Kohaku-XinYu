"""Frame path and data-url helpers for private isolated-desktop routes."""
from __future__ import annotations

import base64
import re
from http import HTTPStatus
from pathlib import Path

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_private_desktop_frame_store import read_private_desktop_frame_bytes
from xinyu_private_desktop_control import FRAMES_REL, LATEST_FRAME_REL

_FRAME_ID_RE = re.compile(r"^[A-Za-z0-9_-]+\.png$")


def _resolve_frame(root: Path, frame_id: str) -> Path:
    """Resolve a frame strictly inside the workspace frames dir, or latest_frame."""
    if not frame_id:
        return root / LATEST_FRAME_REL
    if not _FRAME_ID_RE.match(frame_id):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "invalid frame_id")
    frames_dir = (root / FRAMES_REL).resolve()
    candidate = (frames_dir / frame_id).resolve()
    if candidate.parent != frames_dir:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "frame_id_out_of_bounds")
    return candidate


def _read_frame_data_url(path: Path) -> str:
    try:
        raw = read_private_desktop_frame_bytes(path)
    except OSError:
        return ""
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def _frame_ref(frame_id: str) -> str:
    return (FRAMES_REL / frame_id).as_posix() if frame_id else LATEST_FRAME_REL.as_posix()
