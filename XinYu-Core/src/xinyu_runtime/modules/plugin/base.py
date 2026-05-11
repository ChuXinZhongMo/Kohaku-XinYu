"""Plugin protocol and base class for XinYu Runtime.

Two extension patterns:

**Pre/post hooks** 鈥?wrap existing methods via decoration at init time.
The manager runs pre_* hooks before the real call (can transform input
or block), then the real call, then post_* hooks (can transform output).
All plugins run linearly by priority, not nested.

**Callbacks** 鈥?fire-and-forget notifications with data.

Error handling:
  - PluginBlockError in pre_tool_execute / pre_tool_dispatch:
    blocks execution, becomes tool result
  - Regular Exception: logged, plugin skipped, execution continues
"""

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from xinyu_runtime.utils.logging import get_logger

if TYPE_CHECKING:
    from xinyu_runtime.core.agent import Agent
    from xinyu_runtime.core.compact import CompactManager
    from xinyu_runtime.core.controller import Controller
    from xinyu_runtime.core.registry import Registry
    from xinyu_runtime.core.scratchpad import Scratchpad
    from xinyu_runtime.modules.subagent.manager import SubAgentManager
    from xinyu_runtime.session.memory import SessionMemory
    from xinyu_runtime.session.store import SessionStore


logger = get_logger(__name__)


class PluginBlockError(Exception):
    """Raised by a plugin to block tool/sub-agent execution.

    The error message is returned to the model as the tool result.
    Only meaningful in ``pre_tool_execute``, ``pre_tool_dispatch``, and
    ``pre_subagent_run``.
    """


class PluginContext:
    """Context provided to plugins on load.

    Public accessor surface (read-only properties):

    * ``host_agent`` 鈥?the Agent this plugin is attached to.
    * ``session_store`` 鈥?persistence layer (may be ``None``).
    * ``session_memory`` 鈥?FTS/vector memory (may be ``None`` if disabled).
    * ``registry`` 鈥?tool/sub-agent registry.
    * ``scratchpad`` 鈥?session-scoped key/value store.
    * ``compact_manager`` 鈥?auto-compact controller (may be ``None``).
    * ``controller`` 鈥?LLM conversation loop.
    * ``subagent_manager`` 鈥?sub-agent lifecycle manager.

    Helpers:

    * ``switch_model(name)`` 鈥?hot-swap the LLM profile.
    * ``inject_event(event)`` 鈥?push a ``TriggerEvent`` into the queue.
    * ``inject_message_before_llm(role, content)`` 鈥?queue a message to be
      prepended to the next LLM call.
    * ``get_state(key)`` / ``set_state(key, value)`` 鈥?plugin-scoped state.

    The deprecated ``_agent`` alias was removed in Cluster 2 (尾) of the
    extension-point work. Use ``host_agent`` (or the specific typed
    properties above) instead.
    """

    def __init__(
        self,
        agent_name: str = "",
        working_dir: Path | None = None,
        session_id: str = "",
        model: str = "",
        _host_agent: Any = None,
        _plugin_name: str = "",
    ) -> None:
        self.agent_name = agent_name
        self.working_dir = working_dir if working_dir is not None else Path.cwd()
        self.session_id = session_id
        self.model = model
        self._host_agent = _host_agent
        self._plugin_name = _plugin_name

    def __repr__(self) -> str:
        return (
            f"PluginContext(agent_name={self.agent_name!r}, "
            f"session_id={self.session_id!r}, model={self.model!r}, "
            f"plugin={self._plugin_name!r})"
        )

    # 鈹€鈹€ Public accessors 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    @property
    def host_agent(self) -> "Agent | None":
        """The Agent this plugin is attached to (``None`` pre-load)."""
        return self._host_agent

    @property
    def session_store(self) -> "SessionStore | None":
        """SessionStore for persistent state, or ``None`` if not attached."""
        agent = self._host_agent
        if agent is None:
            return None
        return getattr(agent, "session_store", None)

    @property
    def session_memory(self) -> "SessionMemory | None":
        """SessionMemory for FTS/vector search, or ``None`` if disabled.

        Agents that do not enable memory indexing return ``None``.
        Plugins that need a memory object may construct their own via
        ``session.memory.SessionMemory`` using ``session_store``.
        """
        agent = self._host_agent
        if agent is None:
            return None
        return getattr(agent, "session_memory", None)

    @property
    def registry(self) -> "Registry | None":
        """Tool/sub-agent registry."""
        agent = self._host_agent
        if agent is None:
            return None
        return getattr(agent, "registry", None)

    @property
    def scratchpad(self) -> "Scratchpad | None":
        """Session-scoped key/value scratchpad."""
        agent = self._host_agent
        if agent is None:
            return None
        return getattr(agent, "scratchpad", None)

    @property
    def compact_manager(self) -> "CompactManager | None":
        """Auto-compact controller (may be ``None``)."""
        agent = self._host_agent
        if agent is None:
            return None
        return getattr(agent, "compact_manager", None)

    @property
    def controller(self) -> "Controller | None":
        """LLM conversation loop."""
        agent = self._host_agent
        if agent is None:
            return None
        return getattr(agent, "controller", None)

    @property
    def subagent_manager(self) -> "SubAgentManager | None":
        """Sub-agent lifecycle manager."""
        agent = self._host_agent
        if agent is None:
            return None
        return getattr(agent, "subagent_manager", None)

    # 鈹€鈹€ Helpers 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def switch_model(self, name: str) -> str:
        """Switch the LLM model. Returns resolved model name."""
        agent = self._host_agent
        if agent is not None and hasattr(agent, "switch_model"):
            return agent.switch_model(name)
        return ""

    def inject_event(self, event: Any) -> None:
        """Push a trigger event into the agent's event queue."""
        agent = self._host_agent
        if agent is not None and hasattr(agent, "controller"):
            agent.controller.push_event_sync(event)

    def inject_message_before_llm(self, role: str, content: str | list) -> None:
        """Queue a message to be prepended to the next LLM call.

        The message is drained by the controller just before
        ``pre_llm_call`` hooks run, so all registered plugins observe
        the injected message in ``messages`` too. If the host agent is
        not yet bound, the call is a no-op.
        """
        controller = self.controller
        if controller is None:
            return
        queue = getattr(controller, "_pending_injections", None)
        if queue is None:
            queue = []
            controller._pending_injections = queue
        queue.append({"role": role, "content": content})

    def get_state(self, key: str) -> Any:
        """Read plugin-scoped state from session store."""
        store = self.session_store
        if store is None:
            return None
        return store.state.get(f"plugin:{self._plugin_name}:{key}")

    def set_state(self, key: str, value: Any) -> None:
        """Write plugin-scoped state to session store."""
        store = self.session_store
        if store is None:
            return
        store.state[f"plugin:{self._plugin_name}:{key}"] = value


class BasePlugin:
    """Base class for plugins. Override only what you need.

    Pre/post hooks run linearly by priority around real methods:
        pre_xxx  鈫?real method 鈫?post_xxx

    Return None from pre/post to keep the value unchanged.
    Return a value to replace it for the next plugin in the chain.

    Declarative gating via ``applies_to``:
        class MyPlugin(BasePlugin):
            applies_to = {
                "agent_names": ["swe"],        # list of exact matches
                "model_patterns": ["^codex/"], # list of regex strings
            }

    Override ``should_apply(context)`` for dynamic gating; subclasses
    typically call ``super().should_apply(context)`` first.
    """

    name: str = "unnamed"
    priority: int = 50  # Lower = runs first in pre, last in post

    # Declarative filter. Empty dict / missing = apply to all contexts.
    applies_to: dict[str, list[str]] = {}

    def __init__(self) -> None:
        self._model_pattern_res = self._compile_model_patterns()

    def _compile_model_patterns(self) -> list[re.Pattern[str]]:
        # Pre-compile model_patterns once. Evaluated before every hook
        # call (see cluster 2.5 of the extension-point spec).
        compiled: list[re.Pattern[str]] = []
        for pattern in self.applies_to.get("model_patterns", []) or []:
            try:
                compiled.append(re.compile(pattern))
            except re.error as exc:
                logger.warning(
                    "Plugin model_patterns regex failed to compile; skipping",
                    plugin_name=getattr(self, "name", "?"),
                    pattern=str(pattern),
                    error=str(exc),
                )
        return compiled

    def _model_patterns(self) -> list[re.Pattern[str]]:
        patterns = getattr(self, "_model_pattern_res", None)
        if patterns is None:
            patterns = self._compile_model_patterns()
            self._model_pattern_res = patterns
        return patterns

    # 鈹€鈹€ Gating 鈹€鈹€

    def should_apply(self, context: PluginContext) -> bool:
        """Return True if this plugin should run for the given context.

        Default implementation consults the declarative ``applies_to``
        filter. Override to add dynamic checks 鈥?call
        ``super().should_apply(context)`` first to keep the declarative
        gate in effect.
        """
        applies_to = self.applies_to or {}
        names = applies_to.get("agent_names") or []
        if names and context.agent_name not in names:
            return False
        model_patterns = self._model_patterns()
        if model_patterns:
            model = context.model or ""
            if not any(p.search(model) for p in model_patterns):
                return False
        return True

    # 鈹€鈹€ Controller / package commands 鈹€鈹€

    def contribute_commands(self) -> dict[str, Any]:
        """Return a mapping of ``##name##`` 鈫?``BaseCommand`` instance.

        Called once per plugin after ``on_load``. Built-in command names
        (``info``, ``read_job``, ``jobs``, ``wait``) are protected 鈥?        attempting to register one without ``override=True`` raises.
        """
        return {}

    # 鈹€鈹€ Termination voting 鈹€鈹€

    def contribute_termination_check(
        self,
    ) -> "Callable[[Any], Any] | None":
        """Return a checker function that votes on termination each turn.

        The checker is a callable ``fn(context: TerminationContext) ->
        TerminationDecision | None``. Return ``None`` (default) to not
        participate in termination voting.

        When any plugin's checker returns ``TerminationDecision(
        should_stop=True, reason=...)``, the run stops (any-can-stop
        per cluster 3.3).
        """
        return None

    # 鈹€鈹€ Lifecycle 鈹€鈹€

    async def on_load(self, context: PluginContext) -> None:
        """Called when plugin is loaded."""

    async def on_unload(self) -> None:
        """Called when agent shuts down."""

    # 鈹€鈹€ LLM hooks 鈹€鈹€

    async def pre_llm_call(self, messages: list[dict], **kwargs) -> list[dict] | None:
        """Before LLM call. Return modified messages or None.

        kwargs: model (str), tools (list | None, native mode only)
        """
        return None

    async def post_llm_call(
        self, messages: list[dict], response: str, usage: dict, **kwargs
    ) -> str | None:
        """After LLM call. Return a rewritten response string or None.

        Chain-with-return semantics: each plugin sees the previous
        plugin's rewrite. ``None`` means pass through unchanged.
        Finalize-only 鈥?one fire per complete turn with the full
        assistant content.

        kwargs: model (str)
        """
        return None

    # 鈹€鈹€ Tool hooks 鈹€鈹€

    async def pre_tool_dispatch(self, call: Any, context: PluginContext) -> Any | None:
        """Before the executor sees a tool call.

        Fires after the parser emits a ``ToolCallEvent`` and before the
        executor submits it. Return a new/modified ``ToolCallEvent`` to
        rewrite (can change tool name, args, or both). Return ``None``
        to pass through. Raise ``PluginBlockError`` to veto the call;
        the error text becomes the tool result.

        Chain linearly by priority; each plugin sees the output of the
        previous one.
        """
        return None

    async def pre_tool_execute(self, args: dict, **kwargs) -> dict | None:
        """Before tool execution. Return modified args or None.

        kwargs: tool_name (str), job_id (str)
        Raise PluginBlockError to prevent execution.
        """
        return None

    async def post_tool_execute(self, result: Any, **kwargs) -> Any | None:
        """After tool execution. Return modified result or None.

        kwargs: tool_name (str), job_id (str), args (dict)
        """
        return None

    # 鈹€鈹€ Sub-agent hooks 鈹€鈹€

    async def pre_subagent_run(self, task: str, **kwargs) -> str | None:
        """Before sub-agent run. Return modified task or None.

        kwargs: name (str), job_id (str), is_background (bool)
        Raise PluginBlockError to prevent execution.
        """
        return None

    async def post_subagent_run(self, result: Any, **kwargs) -> Any | None:
        """After sub-agent run. Return modified result or None.

        kwargs: name (str), job_id (str)
        """
        return None

    # 鈹€鈹€ Callbacks (fire-and-forget) 鈹€鈹€

    async def on_agent_start(self) -> None:
        """Called after agent.start() completes."""

    async def on_agent_stop(self) -> None:
        """Called before agent.stop() begins."""

    async def on_event(self, event: Any) -> None:
        """Called on incoming trigger event. Observation only."""

    async def on_interrupt(self) -> None:
        """Called when user interrupts the agent."""

    async def on_task_promoted(self, job_id: str, tool_name: str) -> None:
        """Called when a direct task is promoted to background."""

    async def on_compact_start(self, context_length: int) -> bool | None:
        """Called before context compaction.

        Return ``False`` to veto this compaction cycle 鈥?the manager
        will skip compaction entirely and ``on_compact_end`` will not
        fire. Any other return value (``None``, ``True``) proceeds.

        If multiple plugins implement this hook, compaction proceeds
        only when no plugin returns ``False``.
        """
        return None

    async def on_compact_end(self, summary: str, messages_removed: int) -> None:
        """Called after context compaction (only when not vetoed)."""

