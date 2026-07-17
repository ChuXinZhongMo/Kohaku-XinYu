from __future__ import annotations

from typing import Any

import xinyu_bridge_autonomous_maintenance


def install_autonomous_maintenance_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls._autonomous_maintenance_loop = xinyu_bridge_autonomous_maintenance.autonomous_maintenance_loop
    runtime_cls._ensure_autonomous_session = xinyu_bridge_autonomous_maintenance.ensure_autonomous_session
    runtime_cls._run_autonomous_maintenance_once = xinyu_bridge_autonomous_maintenance.run_autonomous_maintenance_once
    runtime_cls._run_autonomous_self_thought_sidecars = (
        xinyu_bridge_autonomous_maintenance.run_autonomous_self_thought_sidecars
    )
    runtime_cls._append_watched_source_note = xinyu_bridge_autonomous_maintenance.append_watched_source_note
    runtime_cls._append_github_learning_note = xinyu_bridge_autonomous_maintenance.append_github_learning_note
    runtime_cls._append_agent_tech_scout_note = xinyu_bridge_autonomous_maintenance.append_agent_tech_scout_note
    runtime_cls._append_daily_digest_note = xinyu_bridge_autonomous_maintenance.append_daily_digest_note
    runtime_cls._append_creative_writing_note = xinyu_bridge_autonomous_maintenance.append_creative_writing_note
    runtime_cls._append_review_inbox_note = xinyu_bridge_autonomous_maintenance.append_review_inbox_note
    runtime_cls._append_goldmark_dehydrate_note = xinyu_bridge_autonomous_maintenance.append_goldmark_dehydrate_note
    runtime_cls._append_goal_ecology_note = xinyu_bridge_autonomous_maintenance.append_goal_ecology_note
    runtime_cls._append_action_followup_audit_note = (
        xinyu_bridge_autonomous_maintenance.append_action_followup_audit_note
    )
    runtime_cls._append_self_action_gateway_note = xinyu_bridge_autonomous_maintenance.append_self_action_gateway_note
    runtime_cls._append_self_action_patch_executor_note = (
        xinyu_bridge_autonomous_maintenance.append_self_action_patch_executor_note
    )
    runtime_cls._append_self_thought_loop_note = xinyu_bridge_autonomous_maintenance.append_self_thought_loop_note
    runtime_cls._append_proactive_request_note = xinyu_bridge_autonomous_maintenance.append_proactive_request_note
    runtime_cls._append_self_exploration_note = xinyu_bridge_autonomous_maintenance.append_self_exploration_note
    runtime_cls._append_learning_closed_loop_self_thought_note = (
        xinyu_bridge_autonomous_maintenance.append_learning_closed_loop_self_thought_note
    )
    runtime_cls._append_self_thought_research_notes = (
        xinyu_bridge_autonomous_maintenance.append_self_thought_research_notes
    )
    runtime_cls._append_desktop_proactive_candidate_ready_note = (
        xinyu_bridge_autonomous_maintenance.append_desktop_proactive_candidate_ready_note
    )
    runtime_cls._append_autonomous_outcome_shadow_notes = (
        xinyu_bridge_autonomous_maintenance.append_autonomous_outcome_shadow_notes
    )
    runtime_cls._append_autonomous_outward_note = xinyu_bridge_autonomous_maintenance.append_autonomous_outward_note
    runtime_cls._append_goal_outcome_observer_note = (
        xinyu_bridge_autonomous_maintenance.append_goal_outcome_observer_note
    )
    runtime_cls._append_proactivity_shadow_note = xinyu_bridge_autonomous_maintenance.append_proactivity_shadow_note
    runtime_cls._append_emotion_council_note = xinyu_bridge_autonomous_maintenance.append_emotion_council_note
    runtime_cls._append_impulse_soup_note = xinyu_bridge_autonomous_maintenance.append_impulse_soup_note
    runtime_cls._append_initiative_spine_note = xinyu_bridge_autonomous_maintenance.append_initiative_spine_note
    runtime_cls._create_autonomous_maintenance_event = (
        xinyu_bridge_autonomous_maintenance.create_autonomous_maintenance_event
    )
    runtime_cls._record_autonomous_failure = xinyu_bridge_autonomous_maintenance.record_autonomous_failure
    runtime_cls._trace_autonomous = xinyu_bridge_autonomous_maintenance.trace_autonomous
    runtime_cls._write_autonomous_state = xinyu_bridge_autonomous_maintenance.write_autonomous_state
