from __future__ import annotations

from functools import partialmethod
from typing import Any

import xinyu_bridge_promise_followup
from xinyu_bridge_promises import compact_promise_text
from xinyu_visible_persona_voice import compose_promise_followup_message

PROMISE_FOLLOWUP_USER_MARKERS = xinyu_bridge_promise_followup.PROMISE_FOLLOWUP_USER_MARKERS
PROMISE_FOLLOWUP_REPLY_MARKERS = xinyu_bridge_promise_followup.PROMISE_FOLLOWUP_REPLY_MARKERS
PROMISE_FOLLOWUP_DONE_MARKERS = xinyu_bridge_promise_followup.PROMISE_FOLLOWUP_DONE_MARKERS
PROMISE_FOLLOWUP_STATE_REL = xinyu_bridge_promise_followup.PROMISE_FOLLOWUP_STATE_REL


def install_promise_followup_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls._promised_followup_candidate = xinyu_bridge_promise_followup.candidate
    runtime_cls._compact_promise_text = staticmethod(compact_promise_text)
    runtime_cls._schedule_promised_followup_if_needed = partialmethod(
        xinyu_bridge_promise_followup.schedule_if_needed,
        message_func=compose_promise_followup_message,
    )
    runtime_cls._run_promised_followup_review = partialmethod(
        xinyu_bridge_promise_followup.run_review,
        message_func=compose_promise_followup_message,
    )
    runtime_cls._promised_followup_message = staticmethod(compose_promise_followup_message)
    runtime_cls._write_promised_followup_state = partialmethod(
        xinyu_bridge_promise_followup.write_state,
        state_rel=PROMISE_FOLLOWUP_STATE_REL,
    )
    runtime_cls._owner_private_user_id = xinyu_bridge_promise_followup.owner_private_user_id
