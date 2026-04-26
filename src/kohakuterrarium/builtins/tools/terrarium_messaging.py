"""
Terrarium messaging tools for the root agent.

Send messages, observe channels, and read history.
"""

from typing import Any

from kohakuterrarium.builtins.tool_catalog import register_builtin
from kohakuterrarium.builtins.tools.terrarium_lifecycle import _get_manager
from kohakuterrarium.core.channel import ChannelMessage
from kohakuterrarium.modules.tool.base import (
    BaseTool,
    ExecutionMode,
    ToolContext,
    ToolResult,
)
from kohakuterrarium.modules.trigger.channel import ChannelTrigger
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


@register_builtin("terrarium_send")
class TerrariumSendTool(BaseTool):
    """Send a message to a channel in a terrarium."""

    needs_context = True

    @property
    def tool_name(self) -> str:
        return "terrarium_send"

    @property
    def description(self) -> str:
        return "Send a message to a channel in a running terrarium"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "terrarium_id": {
                    "type": "string",
                    "description": "Terrarium ID",
                },
                "channel": {
                    "type": "string",
                    "description": "Channel name to send to",
                },
                "message": {
                    "type": "string",
                    "description": "Message content",
                },
            },
            "required": ["terrarium_id", "channel", "message"],
        }

    async def _execute(
        self, args: dict[str, Any], context: ToolContext | None = None
    ) -> ToolResult:
        manager = _get_manager(context)

        terrarium_id = args.get("terrarium_id", "").strip()
        channel_name = args.get("channel", "").strip()
        message = args.get("message", "").strip()

        if not all([terrarium_id, channel_name, message]):
            return ToolResult(
                error="terrarium_id, channel, and message are all required"
            )

        try:
            runtime = manager.get_runtime(terrarium_id)
            ch = runtime.environment.shared_channels.get(channel_name)
            if ch is None:
                available = runtime.environment.shared_channels.list_channels()
                ch_names = [info["name"] for info in available]
                return ToolResult(
                    error=f"Channel '{channel_name}' not found. Available: {ch_names}"
                )

            sender = context.agent_name if context else "root"
            msg = ChannelMessage(sender=sender, content=message)
            await ch.send(msg)

            return ToolResult(
                output=f"Message sent to [{channel_name}] in {terrarium_id}.",
                exit_code=0,
            )
        except KeyError as e:
            return ToolResult(error=str(e))


@register_builtin("terrarium_observe")
class TerrariumObserveTool(BaseTool):
    """Subscribe/unsubscribe to a terrarium channel.

    Sets up a persistent ChannelTrigger on the agent. New messages
    on the channel automatically trigger the agent. Returns immediately.
    Use enabled=false to stop watching.
    """

    needs_context = True

    @property
    def tool_name(self) -> str:
        return "terrarium_observe"

    @property
    def description(self) -> str:
        return "Watch a terrarium channel (persistent subscription, messages arrive as events)"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "terrarium_id": {
                    "type": "string",
                    "description": "Terrarium ID",
                },
                "channel": {
                    "type": "string",
                    "description": "Channel name to watch",
                },
                "enabled": {
                    "type": "boolean",
                    "description": "True to start watching, false to stop (default true)",
                },
            },
            "required": ["terrarium_id", "channel"],
        }

    async def _execute(
        self, args: dict[str, Any], context: ToolContext | None = None
    ) -> ToolResult:
        manager = _get_manager(context)

        terrarium_id = args.get("terrarium_id", "").strip()
        channel_name = args.get("channel", "").strip()
        enabled = args.get("enabled", True)
        if isinstance(enabled, str):
            enabled = enabled.lower() not in ("false", "0", "no")

        if not terrarium_id or not channel_name:
            return ToolResult(error="terrarium_id and channel are required")

        if not context or not context.agent:
            return ToolResult(error="Agent context required for observe")

        trigger_id = f"observe_{terrarium_id}_{channel_name}"

        if not enabled:
            removed = await context.agent.trigger_manager.remove(trigger_id)
            if removed:
                return ToolResult(
                    output=f"Stopped watching [{channel_name}].", exit_code=0
                )
            return ToolResult(output=f"Was not watching [{channel_name}].", exit_code=0)

        # Check if already watching
        if context.agent.trigger_manager.get(trigger_id):
            return ToolResult(output=f"Already watching [{channel_name}].", exit_code=0)

        try:
            runtime = manager.get_runtime(terrarium_id)
            ch = runtime.environment.shared_channels.get(channel_name)
            if ch is None:
                available = runtime.environment.shared_channels.list_channels()
                ch_names = [info["name"] for info in available]
                return ToolResult(
                    error=f"Channel '{channel_name}' not found. Available: {ch_names}"
                )

            trigger = ChannelTrigger(
                channel_name=channel_name,
                subscriber_id=f"root_{channel_name}",
                ignore_sender=context.agent_name,
                registry=runtime.environment.shared_channels,
            )
            await context.agent.trigger_manager.add(trigger, trigger_id=trigger_id)

            return ToolResult(
                output=f"Now watching [{channel_name}]. Messages will arrive automatically.",
                exit_code=0,
            )

        except KeyError as e:
            return ToolResult(error=str(e))


@register_builtin("terrarium_history")
class TerrariumHistoryTool(BaseTool):
    """Read recent message history from a terrarium channel."""

    needs_context = True

    @property
    def tool_name(self) -> str:
        return "terrarium_history"

    @property
    def description(self) -> str:
        return "Read the last K messages from a terrarium channel"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "terrarium_id": {
                    "type": "string",
                    "description": "Terrarium ID",
                },
                "channel": {
                    "type": "string",
                    "description": "Channel name to read history from",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of recent messages to return (default 10)",
                },
            },
            "required": ["terrarium_id", "channel"],
        }

    async def _execute(
        self, args: dict[str, Any], context: ToolContext | None = None
    ) -> ToolResult:
        manager = _get_manager(context)

        terrarium_id = args.get("terrarium_id", "").strip()
        channel_name = args.get("channel", "").strip()
        limit = int(args.get("limit", 10))

        if not terrarium_id or not channel_name:
            return ToolResult(error="terrarium_id and channel are required")

        try:
            runtime = manager.get_runtime(terrarium_id)
            ch = runtime.environment.shared_channels.get(channel_name)
            if ch is None:
                available = runtime.environment.shared_channels.list_channels()
                ch_names = [info["name"] for info in available]
                return ToolResult(
                    error=f"Channel '{channel_name}' not found. Available: {ch_names}"
                )

            messages = ch.history[-limit:]

            if not messages:
                return ToolResult(
                    output=f"No messages in [{channel_name}].",
                    exit_code=0,
                )

            lines = [f"Last {len(messages)} message(s) in [{channel_name}]:"]
            for msg in messages:
                ts = msg.timestamp.strftime("%H:%M:%S")
                content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
                lines.append(f"  [{ts}] {msg.sender}: {content}")

            return ToolResult(output="\n".join(lines), exit_code=0)

        except KeyError as e:
            return ToolResult(error=str(e))
