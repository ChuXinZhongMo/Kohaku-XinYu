"""Verify backward-compatible re-exports after file splits."""

import pytest

REEXPORT_CASES = [
    # widgets package
    ("kohakuterrarium.builtins.tui.widgets", "ToolBlock"),
    ("kohakuterrarium.builtins.tui.widgets", "SubAgentBlock"),
    ("kohakuterrarium.builtins.tui.widgets", "UserMessage"),
    ("kohakuterrarium.builtins.tui.widgets", "QueuedMessage"),
    ("kohakuterrarium.builtins.tui.widgets", "SystemNotice"),
    ("kohakuterrarium.builtins.tui.widgets", "TriggerMessage"),
    ("kohakuterrarium.builtins.tui.widgets", "StreamingText"),
    ("kohakuterrarium.builtins.tui.widgets", "RunningPanel"),
    ("kohakuterrarium.builtins.tui.widgets", "ScratchpadPanel"),
    ("kohakuterrarium.builtins.tui.widgets", "SessionInfoPanel"),
    ("kohakuterrarium.builtins.tui.widgets", "CompactSummaryBlock"),
    ("kohakuterrarium.builtins.tui.widgets", "TerrariumPanel"),
    ("kohakuterrarium.builtins.tui.widgets", "LoadOlderButton"),
    ("kohakuterrarium.builtins.tui.widgets", "ChatInput"),
    ("kohakuterrarium.builtins.tui.widgets", "SelectionModal"),
    ("kohakuterrarium.builtins.tui.widgets", "ConfirmModal"),
    # profiles re-exports
    ("kohakuterrarium.llm.profiles", "PRESETS"),
    ("kohakuterrarium.llm.profiles", "LLMProfile"),
    ("kohakuterrarium.llm.profiles", "PROVIDER_KEY_MAP"),
    ("kohakuterrarium.llm.profiles", "get_api_key"),
    ("kohakuterrarium.llm.profiles", "list_api_keys"),
    ("kohakuterrarium.llm.profiles", "save_api_key"),
    ("kohakuterrarium.llm.profiles", "resolve_controller_llm"),
    ("kohakuterrarium.llm.profiles", "_is_available"),
    # config re-exports
    ("kohakuterrarium.core.config", "AgentConfig"),
    ("kohakuterrarium.core.config", "InputConfig"),
    ("kohakuterrarium.core.config", "OutputConfig"),
    ("kohakuterrarium.core.config", "SubAgentConfigItem"),
    ("kohakuterrarium.core.config", "load_agent_config"),
    ("kohakuterrarium.core.config", "build_agent_config"),
    # subagent re-exports
    ("kohakuterrarium.modules.subagent", "SubAgentManager"),
    ("kohakuterrarium.modules.subagent", "SubAgent"),
    ("kohakuterrarium.modules.subagent", "SubAgentResult"),
    # agent_init moved to bootstrap
    ("kohakuterrarium.bootstrap.agent_init", "AgentInitMixin"),
]


@pytest.mark.parametrize(
    "module,name", REEXPORT_CASES, ids=[f"{m}.{n}" for m, n in REEXPORT_CASES]
)
def test_reexport(module, name):
    import importlib

    mod = importlib.import_module(module)
    assert hasattr(mod, name), f"{module} does not export {name}"
