from __future__ import annotations

import asyncio
import threading


def start_loop_thread() -> tuple[asyncio.AbstractEventLoop, threading.Thread]:
    ready = threading.Event()
    holder: dict[str, asyncio.AbstractEventLoop] = {}

    def run_loop() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        holder["loop"] = loop
        ready.set()
        loop.run_forever()
        pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

    thread = threading.Thread(target=run_loop, name="xinyu-core-bridge-loop", daemon=True)
    thread.start()
    ready.wait(timeout=10)
    loop = holder.get("loop")
    if loop is None:
        raise RuntimeError("failed to start asyncio loop")
    return loop, thread
