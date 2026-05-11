from xinyu_runtime.modules.plugin.base import BasePlugin, PluginContext
from xinyu_runtime.modules.plugin.manager import _plugin_applies


class MissingSuperInitPlugin(BasePlugin):
    name = "missing_super_init"
    applies_to = {
        "agent_names": ["xinyu"],
        "model_patterns": ["^mimo-"],
    }

    def __init__(self) -> None:
        self.ready = True


def test_should_apply_lazily_initializes_model_patterns() -> None:
    plugin = MissingSuperInitPlugin()

    assert not hasattr(plugin, "_model_pattern_res")
    assert plugin.should_apply(PluginContext(agent_name="xinyu", model="gpt-5.5")) is False
    assert plugin.should_apply(PluginContext(agent_name="xinyu", model="mimo-v2.5-pro")) is True
    assert hasattr(plugin, "_model_pattern_res")


def test_plugin_manager_does_not_default_to_true_for_missing_super_init() -> None:
    plugin = MissingSuperInitPlugin()

    assert _plugin_applies(plugin, PluginContext(agent_name="xinyu", model="gpt-5.5")) is False
