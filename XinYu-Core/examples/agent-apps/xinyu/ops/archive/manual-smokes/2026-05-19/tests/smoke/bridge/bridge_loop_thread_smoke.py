from __future__ import annotations

import asyncio

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_loop_thread import start_loop_thread
from xinyu_core_bridge import _start_loop_thread


async def _answer() -> int:
    await asyncio.sleep(0)
    return 42


def main() -> int:
    failures: list[str] = []

    if _start_loop_thread is not start_loop_thread:
        failures.append("core bridge loop thread alias no longer delegates")

    loop, thread = start_loop_thread()
    try:
        if not thread.is_alive():
            failures.append("loop thread did not start")
        result = asyncio.run_coroutine_threadsafe(_answer(), loop).result(timeout=5)
        if result != 42:
            failures.append("loop thread did not execute coroutine")
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)

    if thread.is_alive():
        failures.append("loop thread did not stop")

    if failures:
        print("XinYu bridge loop thread smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge loop thread smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
