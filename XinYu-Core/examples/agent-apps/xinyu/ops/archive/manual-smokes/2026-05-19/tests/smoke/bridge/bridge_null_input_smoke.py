from __future__ import annotations

import asyncio

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_null_input import NullInputModule
from xinyu_core_bridge import _NullInputModule


async def _main_async() -> list[str]:
    failures: list[str] = []
    module = NullInputModule()

    await module.start()
    await module.stop()
    module.set_user_commands({"ping": object()}, {"ctx": True})
    if not hasattr(module, "_user_commands") or not hasattr(module, "_user_command_context"):
        failures.append("null input module did not store user command context")

    try:
        await asyncio.wait_for(module.get_input(), timeout=0.01)
        failures.append("null input module returned input unexpectedly")
    except TimeoutError:
        pass

    if _NullInputModule is not NullInputModule:
        failures.append("core null input module alias no longer delegates")
    return failures


def main() -> int:
    failures = asyncio.run(_main_async())
    if failures:
        print("XinYu bridge null input smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge null input smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
