from __future__ import annotations

import asyncio
from typing import Any


class NullInputModule:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def get_input(self) -> Any:
        await asyncio.sleep(3600)
        return None

    def set_user_commands(self, commands: dict[str, Any], context: Any) -> None:
        self._user_commands = commands
        self._user_command_context = context
