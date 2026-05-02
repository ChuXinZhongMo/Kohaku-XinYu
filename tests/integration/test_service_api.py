"""Integration tests for the core service API (events, AgentSession, KohakuManager).

These tests exercise the API surface defined in ideas/api-design.md.
The implementation files live in src/kohakuterrarium/serving/:
  - events.py       (ChannelEvent, OutputEvent)
  - agent_session.py (AgentSession)
  - manager.py       (KohakuManager)
"""

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from kohakuterrarium.serving.events import ChannelEvent, OutputEvent
from kohakuterrarium.testing.llm import ScriptedLLM

# Environment patch applied to every test that instantiates agents/terrariums
_FAKE_ENV = {"OPENROUTER_API_KEY": "fake-key-for-test"}
_LLM_PATCH_TARGET = "kohakuterrarium.bootstrap.agent_init.create_llm_provider"


def _scripted_llm(*_args, **_kwargs) -> ScriptedLLM:
    return ScriptedLLM(["OK"])


@pytest.fixture(autouse=True)
def _isolated_runtime():
    """Keep service API tests off real UI, OAuth, and network paths."""
    with patch.dict(os.environ, _FAKE_ENV), patch(
        _LLM_PATCH_TARGET,
        side_effect=_scripted_llm,
    ):
        yield


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


@pytest.fixture()
def terrarium_dir(tmp_path: Path, agent_dir: str) -> str:
    terrarium_path = tmp_path / "novel_terrarium"
    terrarium_path.mkdir()
    rel_agent = Path(agent_dir).as_posix()
    (terrarium_path / "terrarium.yaml").write_text(
        f"""terrarium:
  name: novel_writer
  creatures:
    - name: brainstorm
      config: {rel_agent}
      channels:
        listen: [seed]
        can_send: [ideas]
  channels:
    seed: {{ type: queue, description: "Story seed prompt" }}
    ideas: {{ type: queue, description: "Story ideas" }}
""",
        encoding="utf-8",
    )
    return str(terrarium_path)


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


class TestEventTypes:
    """Verify ChannelEvent and OutputEvent dataclasses."""

    def test_channel_event_creation(self):
        """ChannelEvent has all required fields."""
        event = ChannelEvent(
            terrarium_id="t1",
            channel="ideas",
            sender="brainstorm",
            content="A fresh idea",
            message_id="msg_001",
        )
        assert event.terrarium_id == "t1"
        assert event.channel == "ideas"
        assert event.sender == "brainstorm"
        assert event.content == "A fresh idea"
        assert event.message_id == "msg_001"

    def test_output_event_creation(self):
        """OutputEvent has all required fields."""
        event = OutputEvent(
            agent_id="agent_abc",
            event_type="text",
            content="Hello world",
        )
        assert event.agent_id == "agent_abc"
        assert event.event_type == "text"
        assert event.content == "Hello world"

    def test_channel_event_defaults(self):
        """Timestamp and metadata have sensible defaults."""
        before = datetime.now()
        event = ChannelEvent(
            terrarium_id="t1",
            channel="ch",
            sender="s",
            content="c",
            message_id="m1",
        )
        after = datetime.now()

        assert before <= event.timestamp <= after
        assert event.metadata == {}

    def test_output_event_defaults(self):
        """OutputEvent timestamp and metadata have sensible defaults."""
        before = datetime.now()
        event = OutputEvent(
            agent_id="a1",
            event_type="tool_start",
            content="running bash",
        )
        after = datetime.now()

        assert before <= event.timestamp <= after
        assert event.metadata == {}

    def test_channel_event_custom_metadata(self):
        """ChannelEvent accepts custom metadata dict."""
        event = ChannelEvent(
            terrarium_id="t1",
            channel="ch",
            sender="s",
            content="c",
            message_id="m1",
            metadata={"priority": "high"},
        )
        assert event.metadata == {"priority": "high"}


# ---------------------------------------------------------------------------
# AgentSession
# ---------------------------------------------------------------------------


class TestAgentSession:
    """Test AgentSession lifecycle and status."""

    @pytest.fixture(autouse=True)
    def _env(self):
        """Ensure a fake API key is set for all tests in this class."""
        with patch.dict(os.environ, _FAKE_ENV):
            yield

    async def test_create_from_path(self, agent_dir: str):
        """Create session from config path, verify agent_id, and stop."""
        from kohakuterrarium.serving.agent_session import AgentSession

        session = await AgentSession.from_path(agent_dir)
        try:
            assert session.agent_id is not None
            assert session.agent_id.startswith("agent_")
            assert session._running is True
        finally:
            await session.stop()

    async def test_get_status(self, agent_dir: str):
        """Status includes agent_id, name, running, and tools."""
        from kohakuterrarium.serving.agent_session import AgentSession

        session = await AgentSession.from_path(agent_dir)
        try:
            status = session.get_status()
            assert "agent_id" in status
            assert status["name"] == "swe"
            assert status["running"] is True
            assert isinstance(status["tools"], list)
            assert len(status["tools"]) > 0
        finally:
            await session.stop()

    async def test_session_lifecycle(self, agent_dir: str):
        """Start and stop lifecycle transitions correctly."""
        from kohakuterrarium.serving.agent_session import AgentSession

        agent = __import__(
            "kohakuterrarium.core.agent", fromlist=["Agent"]
        ).Agent.from_path(agent_dir)
        session = AgentSession(agent)

        # Before start
        assert session._running is False

        await session.start()
        assert session._running is True
        assert session.agent.is_running is True

        await session.stop()
        assert session._running is False


# ---------------------------------------------------------------------------
# KohakuManager — Agents
# ---------------------------------------------------------------------------


class TestKohakuManagerAgents:
    """Test KohakuManager standalone agent operations."""

    @pytest.fixture(autouse=True)
    def _env(self):
        with patch.dict(os.environ, _FAKE_ENV):
            yield

    @pytest.fixture()
    async def manager(self):
        """Create a KohakuManager and shut it down after the test."""
        from kohakuterrarium.serving.manager import KohakuManager

        mgr = KohakuManager()
        yield mgr
        await mgr.shutdown()

    async def test_create_agent(self, manager, agent_dir: str):
        """Create a standalone agent and verify it is listed."""
        agent_id = await manager.agent_create(config_path=agent_dir)
        assert agent_id is not None

        agents = manager.agent_list()
        ids = [a["agent_id"] for a in agents]
        assert agent_id in ids

    async def test_stop_agent(self, manager, agent_dir: str):
        """Stop an agent and verify it is removed."""
        agent_id = await manager.agent_create(config_path=agent_dir)
        await manager.agent_stop(agent_id)

        agents = manager.agent_list()
        ids = [a["agent_id"] for a in agents]
        assert agent_id not in ids

    async def test_list_agents(self, manager, agent_dir: str):
        """List returns all running agents."""
        id1 = await manager.agent_create(config_path=agent_dir)
        id2 = await manager.agent_create(config_path=agent_dir)

        agents = manager.agent_list()
        ids = {a["agent_id"] for a in agents}
        assert {id1, id2} <= ids

    async def test_get_agent_status(self, manager, agent_dir: str):
        """Get status of a specific agent."""
        agent_id = await manager.agent_create(config_path=agent_dir)
        status = manager.agent_status(agent_id)

        assert status is not None
        assert status["agent_id"] == agent_id
        assert status["name"] == "swe"
        assert status["running"] is True
        assert isinstance(status["tools"], list)

    async def test_stop_nonexistent_agent(self, manager):
        """Stopping a nonexistent agent does not raise."""
        # Should complete without error
        await manager.agent_stop("nonexistent_agent_id_12345")


# ---------------------------------------------------------------------------
# KohakuManager — Terrariums
# ---------------------------------------------------------------------------


class TestKohakuManagerTerrariums:
    """Test KohakuManager terrarium operations."""

    @pytest.fixture(autouse=True)
    def _env(self):
        with patch.dict(os.environ, _FAKE_ENV):
            yield

    @pytest.fixture()
    async def manager(self):
        """Create a KohakuManager and shut it down after the test."""
        from kohakuterrarium.serving.manager import KohakuManager

        mgr = KohakuManager()
        yield mgr
        await mgr.shutdown()

    async def test_create_terrarium(self, manager, terrarium_dir: str):
        """Create terrarium from config path."""
        tid = await manager.terrarium_create(config_path=terrarium_dir)
        assert tid is not None

        terrariums = manager.terrarium_list()
        ids = [t["terrarium_id"] for t in terrariums]
        assert tid in ids

    async def test_stop_terrarium(self, manager, terrarium_dir: str):
        """Stop terrarium and verify removed."""
        tid = await manager.terrarium_create(config_path=terrarium_dir)
        await manager.terrarium_stop(tid)

        terrariums = manager.terrarium_list()
        ids = [t["terrarium_id"] for t in terrariums]
        assert tid not in ids

    async def test_list_terrariums(self, manager, terrarium_dir: str):
        """List returns running terrariums."""
        tid = await manager.terrarium_create(config_path=terrarium_dir)

        listing = manager.terrarium_list()
        assert len(listing) >= 1
        assert any(t["terrarium_id"] == tid for t in listing)

    async def test_get_terrarium_status(self, manager, terrarium_dir: str):
        """Status includes creatures and channels."""
        tid = await manager.terrarium_create(config_path=terrarium_dir)
        status = manager.terrarium_status(tid)

        assert status is not None
        assert "creatures" in status
        assert "channels" in status
        assert status["running"] is True

    async def test_hot_plug_via_manager(
        self, manager, agent_dir: str, terrarium_dir: str
    ):
        """Add creature/channel through manager."""
        from kohakuterrarium.terrarium.config import CreatureConfig

        tid = await manager.terrarium_create(config_path=terrarium_dir)

        # Add a new channel
        await manager.terrarium_channel_add(
            tid, name="review", channel_type="queue", description="Review notes"
        )

        status = manager.terrarium_status(tid)
        channel_names = [ch["name"] for ch in status["channels"]]
        assert "review" in channel_names

        # Add a new creature wired to the new channel
        creature_cfg = CreatureConfig(
            name="reviewer",
            config_data={"base_config": agent_dir},
            base_dir=Path("."),
            listen_channels=["review"],
            send_channels=[],
        )
        creature_name = await manager.creature_add(tid, config=creature_cfg)
        assert creature_name is not None

        status = manager.terrarium_status(tid)
        assert "reviewer" in status["creatures"]

    async def test_send_to_channel(self, manager, terrarium_dir: str):
        """Send message to channel via manager."""
        tid = await manager.terrarium_create(config_path=terrarium_dir)

        # "seed" channel exists in novel_terrarium config
        msg_id = await manager.terrarium_channel_send(
            tid, channel="seed", content="Write about space.", sender="human"
        )
        assert msg_id is not None
        assert isinstance(msg_id, str)
        assert len(msg_id) > 0


# ---------------------------------------------------------------------------
# KohakuManager — Shutdown
# ---------------------------------------------------------------------------


class TestKohakuManagerShutdown:
    """Test KohakuManager full shutdown."""

    @pytest.fixture(autouse=True)
    def _env(self):
        with patch.dict(os.environ, _FAKE_ENV):
            yield

    async def test_shutdown_stops_everything(
        self, agent_dir: str, terrarium_dir: str
    ):
        """Shutdown stops all agents and terrariums."""
        from kohakuterrarium.serving.manager import KohakuManager

        mgr = KohakuManager()

        await mgr.agent_create(config_path=agent_dir)
        await mgr.terrarium_create(config_path=terrarium_dir)

        # Verify they exist
        assert len(mgr.agent_list()) >= 1
        assert len(mgr.terrarium_list()) >= 1

        await mgr.shutdown()

        assert mgr.agent_list() == []
        assert mgr.terrarium_list() == []
