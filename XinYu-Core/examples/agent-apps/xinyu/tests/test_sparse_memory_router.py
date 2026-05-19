from __future__ import annotations

from types import SimpleNamespace

from xinyu_living_memory_recall import RecalledContextItem
from xinyu_sparse_memory_router import apply_sparse_memory_route, build_sparse_memory_route
from xinyu_storage_paths import knowledge_ref


def _visible(**kwargs: object) -> SimpleNamespace:
    base = {
        "technical_work": False,
        "owner_style_pressure": False,
        "owner_no_change_pressure": False,
        "relationship_pressure": False,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _item(
    source: str,
    summary: str,
    *,
    score: float,
    memory_ref: str = "",
) -> RecalledContextItem:
    return RecalledContextItem(
        recall_id=f"test-{source}",
        source=source,
        scope="owner_private",
        time="test",
        speaker="memory",
        summary=summary,
        relevance="test",
        confidence="medium",
        score=score,
        memory_ref=memory_ref,
    )


def test_direct_recall_activates_recent_dialogue_without_all_experts() -> None:
    route = build_sparse_memory_route(
        query_text="\u521a\u624d\u6211\u8bf4\u4e86\u4ec0\u4e48",
        query_terms=("\u521a\u624d", "\u4ec0\u4e48"),
        direct_recall=True,
    )

    assert "recent_dialogue" in route.selected_experts
    assert route.allows_source("dialogue_tail")
    assert len(route.selected_experts) < len(route.decisions)
    assert "sparse_memory_router_v1" in route.notes


def test_plugin_api_work_activates_project_and_tool_experts() -> None:
    route = build_sparse_memory_route(
        query_text="Kohaku MCP plugin API Codex runtime status",
        query_terms=("Kohaku", "MCP", "plugin", "API", "Codex", "runtime"),
        visible_turn=_visible(technical_work=True),
    )

    assert "project_task" in route.selected_experts
    assert "tool_plugin" in route.selected_experts
    assert route.allows_source("stable_memory")
    assert route.allows_memory_ref("memory/context/codex_delegation_policy.md")
    assert route.allows_memory_ref(knowledge_ref("source_materials.md"))


def test_current_qq_turn_demotes_stale_runtime_memory() -> None:
    route = build_sparse_memory_route(
        query_text="QQ gateway status",
        query_terms=("QQ", "gateway", "status"),
        payload={
            "metadata": {
                "qq_gateway_live_current_turn": True,
                "qq_current_turn_transport": "napcat",
                "qq_current_turn_message_kind": "private_text",
            }
        },
    )

    routed = apply_sparse_memory_route(
        [
            _item(
                "stable_memory",
                "QQ gateway offline old status; NapCat not connected.",
                score=10.0,
                memory_ref="memory/context/recent_context.md",
            ),
            _item(
                "dialogue_tail",
                "QQ gateway live current turn reached the core through NapCat.",
                score=4.0,
            ),
        ],
        route,
    )

    stable = next(item for item in routed.items if item.source == "stable_memory")
    tail = next(item for item in routed.items if item.source == "dialogue_tail")
    assert stable.score < tail.score
    assert "sparse_route_current_turn_penalties:1" in routed.notes
    assert "current_turn_contradiction_penalty" in stable.relevance
