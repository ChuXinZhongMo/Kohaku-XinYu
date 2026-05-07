"""Final response renderer."""

from __future__ import annotations

from ..gateway.models import InboundTurn
from .models import DraftReply, FinalReply
from .safety import check_response_safety
from .speech_controller_adapter import SpeechControllerAdapter
from .voice_gate import clean_voice
from xinyu_visible_reply_guard import dedupe_visible_reply


class ResponseRenderer:
    def __init__(self, speech_adapter: SpeechControllerAdapter | None = None) -> None:
        self._speech_adapter = speech_adapter or SpeechControllerAdapter()

    def render(self, draft: DraftReply, turn: InboundTurn) -> FinalReply:
        text, voice_notes = clean_voice(draft.text)
        text, adapter_notes = self._speech_adapter.refine(text)
        dedupe = dedupe_visible_reply(text)
        text = dedupe.text
        decision = check_response_safety(text, turn)
        notes = (*draft.notes, *voice_notes, *adapter_notes, *dedupe.notes, decision.reason)
        if decision.blocked:
            return FinalReply(text="", accepted=False, notes=notes, metadata={"decision": decision.to_json()})
        return FinalReply(text=text, accepted=True, notes=notes, metadata={"decision": decision.to_json()})
