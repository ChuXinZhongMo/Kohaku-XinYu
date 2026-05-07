"""Regen command — regenerate the last assistant response."""

from xinyu_runtime.builtins.user_commands import register_user_command
from xinyu_runtime.modules.user_command.base import (
    BaseUserCommand,
    CommandLayer,
    UserCommandContext,
    UserCommandResult,
)


@register_user_command("regen")
class RegenCommand(BaseUserCommand):
    name = "regen"
    aliases = ["regenerate"]
    description = "Regenerate the last assistant response with current settings"
    layer = CommandLayer.AGENT

    async def _execute(
        self, args: str, context: UserCommandContext
    ) -> UserCommandResult:
        if not context.agent:
            return UserCommandResult(error="No agent context.")
        await context.agent.regenerate_last_response()
        return UserCommandResult(output="Regenerating last response...")
