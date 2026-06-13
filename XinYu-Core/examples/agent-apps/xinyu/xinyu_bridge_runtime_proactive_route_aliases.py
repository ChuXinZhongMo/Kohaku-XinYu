from __future__ import annotations

from typing import Any

import xinyu_bridge_desktop_proactive_routes
import xinyu_bridge_proactive_delivery_routes


def install_proactive_route_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls.proactive = xinyu_bridge_proactive_delivery_routes.proactive
    runtime_cls.proactive_ack = xinyu_bridge_proactive_delivery_routes.proactive_ack
    runtime_cls.desktop_proactive_ack = xinyu_bridge_desktop_proactive_routes.desktop_proactive_ack
    runtime_cls._record_desktop_initiative_feedback = (
        xinyu_bridge_desktop_proactive_routes.record_desktop_initiative_feedback
    )
    runtime_cls.qq_outbox_claim = xinyu_bridge_proactive_delivery_routes.qq_outbox_claim
    runtime_cls.qq_outbox_claim_fast = xinyu_bridge_proactive_delivery_routes.qq_outbox_claim_fast
    runtime_cls.qq_outbox_ack = xinyu_bridge_proactive_delivery_routes.qq_outbox_ack
    runtime_cls.qq_outbox_ack_fast = xinyu_bridge_proactive_delivery_routes.qq_outbox_ack_fast
    runtime_cls._claim_proactive_for_qq_outbox = (
        xinyu_bridge_proactive_delivery_routes.claim_proactive_for_qq_outbox
    )
    runtime_cls._claim_proactive_for_qq_outbox_sync = (
        xinyu_bridge_proactive_delivery_routes.claim_proactive_for_qq_outbox_sync
    )
    runtime_cls._ready_proactive_outbox_candidate = (
        xinyu_bridge_proactive_delivery_routes.ready_proactive_outbox_candidate
    )
    runtime_cls._proactive_candidate_already_handled = (
        xinyu_bridge_proactive_delivery_routes.proactive_candidate_already_handled
    )
    runtime_cls._desktop_approve_proactive_qq = xinyu_bridge_desktop_proactive_routes.desktop_approve_proactive_qq
    runtime_cls._desktop_finish_proactive_ack = xinyu_bridge_desktop_proactive_routes.desktop_finish_proactive_ack
    runtime_cls._desktop_update_proactive_request_state = (
        xinyu_bridge_desktop_proactive_routes.desktop_update_proactive_request_state
    )
    runtime_cls._desktop_publish_proactive_candidate_ready_from_state = (
        xinyu_bridge_desktop_proactive_routes.desktop_publish_proactive_candidate_ready_from_state
    )
    runtime_cls._desktop_schedule_proactive_candidate_ready_from_state = (
        xinyu_bridge_desktop_proactive_routes.desktop_schedule_proactive_candidate_ready_from_state
    )
    runtime_cls._desktop_publish_initiative_candidate_threadsafe = (
        xinyu_bridge_desktop_proactive_routes.desktop_publish_initiative_candidate_threadsafe
    )
    runtime_cls._desktop_publish_proactive_delivery_from_state = (
        xinyu_bridge_desktop_proactive_routes.desktop_publish_proactive_delivery_from_state
    )
    runtime_cls._desktop_publish_proactive_delivery_item = (
        xinyu_bridge_desktop_proactive_routes.desktop_publish_proactive_delivery_item
    )
    runtime_cls._desktop_publish_proactive_delivery_from_state_threadsafe = (
        xinyu_bridge_desktop_proactive_routes.desktop_publish_proactive_delivery_from_state_threadsafe
    )
    runtime_cls._desktop_proactive_delivery_payload = staticmethod(
        xinyu_bridge_desktop_proactive_routes.desktop_proactive_delivery_payload
    )
    runtime_cls._desktop_apply_proactive_delivery = (
        xinyu_bridge_desktop_proactive_routes.desktop_apply_proactive_delivery
    )
    runtime_cls._desktop_proactive_item_from_state = (
        xinyu_bridge_desktop_proactive_routes.desktop_proactive_item_from_state
    )
    runtime_cls._desktop_proactive_existing = xinyu_bridge_desktop_proactive_routes.desktop_proactive_existing
    runtime_cls._desktop_upsert_proactive_inbox = xinyu_bridge_desktop_proactive_routes.desktop_upsert_proactive_inbox
    runtime_cls._desktop_remove_proactive_inbox = xinyu_bridge_desktop_proactive_routes.desktop_remove_proactive_inbox
    runtime_cls._desktop_remember_proactive_history = (
        xinyu_bridge_desktop_proactive_routes.desktop_remember_proactive_history
    )
    runtime_cls._desktop_load_proactive_history = xinyu_bridge_desktop_proactive_routes.desktop_load_proactive_history
    runtime_cls._desktop_compact_proactive_history = staticmethod(
        xinyu_bridge_desktop_proactive_routes.desktop_compact_proactive_history
    )
    runtime_cls._desktop_remove_proactive_state_items = (
        xinyu_bridge_desktop_proactive_routes.desktop_remove_proactive_state_items
    )
    runtime_cls._desktop_clear_proactive_inbox = xinyu_bridge_desktop_proactive_routes.desktop_clear_proactive_inbox
    runtime_cls._desktop_prune_proactive_inbox = xinyu_bridge_desktop_proactive_routes.desktop_prune_proactive_inbox
    runtime_cls.desktop_proactive_inbox = xinyu_bridge_desktop_proactive_routes.desktop_proactive_inbox
    runtime_cls._record_proactive_outbound_dialogue = (
        xinyu_bridge_proactive_delivery_routes.record_proactive_outbound_dialogue
    )
