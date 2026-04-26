"""Interactive sub-agent management mixin."""

from typing import Any, Callable

from kohakuterrarium.modules.subagent.interactive import (
    InteractiveOutput,
    InteractiveSubAgent,
)
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


class InteractiveManagerMixin:
    """Mixin providing interactive sub-agent management methods.

    Expects the host class to provide:
    - self._configs: dict[str, SubAgentConfig]
    - self._interactive: dict[str, InteractiveSubAgent]
    - self._output_callbacks: dict[str, Callable[[InteractiveOutput], None]]
    - self.parent_registry: Registry
    - self.llm: LLMProvider
    - self.agent_path: Path | None
    - self._tool_format: str | None
    """

    async def start_interactive(
        self,
        name: str,
        on_output: Callable[[InteractiveOutput], None] | None = None,
    ) -> InteractiveSubAgent:
        """
        Start an interactive sub-agent.

        Interactive sub-agents stay alive and receive context updates.

        Args:
            name: Sub-agent name (must be registered with interactive=True)
            on_output: Callback for output chunks

        Returns:
            InteractiveSubAgent instance

        Raises:
            ValueError: If sub-agent not registered or not interactive
        """
        config = self._configs.get(name)
        if config is None:
            raise ValueError(f"Sub-agent not registered: {name}")

        if not config.interactive:
            raise ValueError(f"Sub-agent is not interactive: {name}")

        # Check if already running
        if name in self._interactive:
            logger.warning(
                "Interactive sub-agent already running",
                subagent_name=name,
            )
            return self._interactive[name]

        # Resolve tool_format: config override > parent inherited
        effective_tool_format = config.tool_format or self._tool_format

        # Create interactive sub-agent
        agent = InteractiveSubAgent(
            config=config,
            parent_registry=self.parent_registry,
            llm=self.llm,
            agent_path=self.agent_path,
            tool_format=effective_tool_format,
        )

        # Set output callback
        if on_output:
            agent.on_output = on_output
            self._output_callbacks[name] = on_output

        # Start the agent
        await agent.start()
        self._interactive[name] = agent

        logger.info(
            "Started interactive sub-agent",
            subagent_name=name,
            context_mode=config.context_mode.value,
        )

        return agent

    async def stop_interactive(self, name: str) -> None:
        """
        Stop an interactive sub-agent.

        Args:
            name: Sub-agent name
        """
        agent = self._interactive.get(name)
        if agent:
            await agent.stop()
            del self._interactive[name]
            self._output_callbacks.pop(name, None)

            logger.info("Stopped interactive sub-agent", subagent_name=name)

    async def stop_all_interactive(self) -> None:
        """Stop all running interactive sub-agents."""
        names = list(self._interactive.keys())
        for name in names:
            await self.stop_interactive(name)

    async def push_context(
        self,
        name: str,
        context: dict[str, Any],
    ) -> None:
        """
        Push context update to an interactive sub-agent.

        Args:
            name: Sub-agent name
            context: Context data to push

        Raises:
            ValueError: If sub-agent not running
        """
        agent = self._interactive.get(name)
        if agent is None:
            raise ValueError(f"Interactive sub-agent not running: {name}")

        await agent.push_context(context)

    async def push_context_all(self, context: dict[str, Any]) -> None:
        """
        Push context update to all running interactive sub-agents.

        Args:
            context: Context data to push
        """
        for agent in self._interactive.values():
            await agent.push_context(context)

    def get_interactive(self, name: str) -> InteractiveSubAgent | None:
        """
        Get a running interactive sub-agent.

        Args:
            name: Sub-agent name

        Returns:
            InteractiveSubAgent if running, None otherwise
        """
        return self._interactive.get(name)

    def list_interactive(self) -> list[str]:
        """
        List running interactive sub-agents.

        Returns:
            List of sub-agent names
        """
        return list(self._interactive.keys())

    def get_interactive_output(self, name: str) -> str:
        """
        Get and clear buffered output from interactive sub-agent.

        Used for return_as_context functionality.

        Args:
            name: Sub-agent name

        Returns:
            Buffered output text (empty if not found)
        """
        agent = self._interactive.get(name)
        if agent:
            return agent.get_buffered_output()
        return ""

    def set_output_callback(
        self,
        name: str,
        callback: Callable[[InteractiveOutput], None],
    ) -> None:
        """
        Set output callback for an interactive sub-agent.

        Args:
            name: Sub-agent name
            callback: Callback function for output chunks
        """
        agent = self._interactive.get(name)
        if agent:
            agent.on_output = callback
            self._output_callbacks[name] = callback
