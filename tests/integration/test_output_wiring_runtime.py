"""Integration test: output-wiring resolver is installed by TerrariumRuntime.

This test verifies the end-to-end config → runtime path:

1. A creature config can declare ``output_wiring:``.
2. ``build_agent_config`` parses it into ``list[OutputWiringEntry]``.
3. ``TerrariumRuntime.start()`` builds a ``TerrariumOutputWiringResolver``
   and installs it on every creature's ``_wiring_resolver`` field.
4. The resolver correctly resolves creature names and the magic
   ``root`` target using the live terrarium state.

No LLM calls happen here — we only inspect runtime state after start().
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from kohakuterrarium.core.output_wiring import ROOT_TARGET, OutputWiringEntry
from kohakuterrarium.core.session import remove_session
from kohakuterrarium.testing.llm import ScriptedLLM
from kohakuterrarium.terrarium.config import (
    ChannelConfig,
    CreatureConfig,
    RootConfig,
    TerrariumConfig,
)
from kohakuterrarium.terrarium.output_wiring import TerrariumOutputWiringResolver
from kohakuterrarium.terrarium.runtime import TerrariumRuntime

_FAKE_ENV = {"OPENROUTER_API_KEY": "fake-key-for-test"}
_LLM_PATCH_TARGET = "kohakuterrarium.bootstrap.agent_init.create_llm_provider"


def _scripted_llm(*_args, **_kwargs) -> ScriptedLLM:
    return ScriptedLLM(["OK"])


def _terrarium_config_with_wiring(
    *, include_root: bool, agent_dir: str
) -> TerrariumConfig:
    """Build a tiny two-creature terrarium with output_wiring declared."""
    alpha_config_data: dict = {
        "base_config": agent_dir,
        "output_wiring": [
            {"to": "beta"},
            {"to": "root", "with_content": False},
        ],
    }
    beta_config_data: dict = {
        "base_config": agent_dir,
        "output_wiring": ["alpha"],  # shorthand
    }

    creatures = [
        CreatureConfig(
            name="alpha",
            config_data=alpha_config_data,
            base_dir=Path("."),
            listen_channels=[],
            send_channels=[],
        ),
        CreatureConfig(
            name="beta",
            config_data=beta_config_data,
            base_dir=Path("."),
            listen_channels=[],
            send_channels=[],
        ),
    ]

    root: RootConfig | None = None
    if include_root:
        root = RootConfig(
            config_data={"base_config": agent_dir},
            base_dir=Path("."),
        )

    return TerrariumConfig(
        name="test_wiring_terrarium",
        creatures=creatures,
        channels=[
            ChannelConfig(name="noop_ch", channel_type="queue", description=""),
        ],
        root=root,
    )


@pytest.fixture()
def agent_dir(tmp_path: Path) -> str:
    agent_path = tmp_path / "swe"
    agent_path.mkdir()
    (agent_path / "config.yaml").write_text(
        """name: swe
version: "1.0"
controller:
  model: test-model
  api_key_env: OPENROUTER_API_KEY
  base_url: https://example.invalid/v1
input:
  type: none
output:
  type: stdout
tools:
  - name: read
  - name: bash
""",
        encoding="utf-8",
    )
    return str(agent_path)


@pytest.fixture(autouse=True)
def isolated_runtime():
    """Keep output-wiring runtime tests off real UI, OAuth, and network paths."""
    with patch.dict(os.environ, _FAKE_ENV), patch(
        _LLM_PATCH_TARGET,
        side_effect=_scripted_llm,
    ):
        yield


@pytest.fixture(autouse=True)
def cleanup_sessions():
    yield
    remove_session("terrarium_test_wiring_terrarium")
    # Root agent session is under its own env_id; clean up defensively.
    remove_session("root_test_wiring_terrarium")


class TestOutputWiringConfigFlow:
    async def test_wiring_flows_from_config_to_agent(self, agent_dir: str):
        """Output wiring declared in the YAML reaches AgentConfig.output_wiring."""
        cfg = _terrarium_config_with_wiring(
            include_root=False,
            agent_dir=agent_dir,
        )
        runtime = TerrariumRuntime(cfg)

        await runtime.start()

        try:
            alpha_agent = runtime._creatures["alpha"].agent
            beta_agent = runtime._creatures["beta"].agent

            alpha_wiring = alpha_agent.config.output_wiring
            assert isinstance(alpha_wiring, list)
            assert all(isinstance(e, OutputWiringEntry) for e in alpha_wiring)
            assert [e.to for e in alpha_wiring] == ["beta", "root"]
            assert alpha_wiring[0].with_content is True
            assert alpha_wiring[1].with_content is False

            beta_wiring = beta_agent.config.output_wiring
            assert [e.to for e in beta_wiring] == ["alpha"]
            assert beta_wiring[0].with_content is True
        finally:
            await runtime.stop()


class TestResolverInstallation:
    async def test_every_creature_gets_the_resolver(self, agent_dir: str):
        cfg = _terrarium_config_with_wiring(
            include_root=False,
            agent_dir=agent_dir,
        )
        runtime = TerrariumRuntime(cfg)

        await runtime.start()

        try:
            for name, handle in runtime._creatures.items():
                resolver = handle.agent._wiring_resolver
                assert resolver is not None, f"{name} has no wiring resolver"
                assert isinstance(resolver, TerrariumOutputWiringResolver)
        finally:
            await runtime.stop()

    async def test_root_gets_the_resolver_too(self, agent_dir: str):
        cfg = _terrarium_config_with_wiring(
            include_root=True,
            agent_dir=agent_dir,
        )
        runtime = TerrariumRuntime(cfg)

        await runtime.start()

        try:
            assert runtime._root_agent is not None
            assert isinstance(
                runtime._root_agent._wiring_resolver, TerrariumOutputWiringResolver
            )
        finally:
            await runtime.stop()

    async def test_resolver_resolves_creature_and_root_targets(self, agent_dir: str):
        cfg = _terrarium_config_with_wiring(
            include_root=True,
            agent_dir=agent_dir,
        )
        runtime = TerrariumRuntime(cfg)

        await runtime.start()

        try:
            alpha_agent = runtime._creatures["alpha"].agent
            resolver = alpha_agent._wiring_resolver

            # Resolver correctly resolves another creature by name.
            beta_resolved = resolver._resolve_target("beta")
            assert beta_resolved is runtime._creatures["beta"].agent

            # Resolver correctly resolves the magic 'root' target.
            root_resolved = resolver._resolve_target(ROOT_TARGET)
            assert root_resolved is runtime._root_agent

            # Unknown targets resolve to None.
            assert resolver._resolve_target("unknown") is None
        finally:
            await runtime.stop()
