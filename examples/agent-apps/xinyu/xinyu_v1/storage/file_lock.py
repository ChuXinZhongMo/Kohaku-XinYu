"""Small cross-platform lock-file guard."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from ..errors import MaintenanceLockError


@dataclass(slots=True)
class FileLock:
    path: Path
    timeout_seconds: float = 0.0
    poll_seconds: float = 0.05

    _fd: int | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        while True:
            try:
                self._fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._fd, str(os.getpid()).encode("ascii", errors="ignore"))
                return
            except FileExistsError as exc:
                if self.timeout_seconds <= 0 or time.monotonic() - started >= self.timeout_seconds:
                    raise MaintenanceLockError("lock is already held", details={"path": str(self.path)}) from exc
                time.sleep(self.poll_seconds)

    def release(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            finally:
                self._fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()

