from __future__ import annotations

import asyncio

from xinyu_qq_gateway import GatewayConfig, NativeQQGateway, PreparedMessage, ReplyTarget


class _ReplyClient:
    async def chat(self, payload):
        return {"accepted": True, "reply": "old reply", "route": "chat"}


class _StaleGateway(NativeQQGateway):
    def __init__(self) -> None:
        super().__init__(
            GatewayConfig(
                bridge_token="smoke-token",
                whitelist_user_ids=frozenset({"42"}),
                owner_user_ids=frozenset({"42"}),
                owner_private_coalesce_seconds=0.0,
            )
        )
        self.client = _ReplyClient()
        self.replies: list[str] = []
        self.traces: list[dict[str, str]] = []

    async def send_reply(self, websocket, target, text):
        self.replies.append(text)
        return {"status": "ok"}

    def _trace_qq_inbound(
        self,
        event,
        *,
        stage,
        arrival_seq=0,
        prepared=None,
        session_queue_key="",
        queue_depth=None,
        drop_reason="",
        error="",
    ):
        self.traces.append({"stage": stage, "drop_reason": drop_reason})

    def _trace_qq_rich_context(self, event, prepared, *, stage):
        return None


def test_owner_private_reply_is_dropped_when_newer_input_arrived() -> None:
    async def _run() -> None:
        gateway = _StaleGateway()
        event = {"post_type": "message", "message_type": "private", "user_id": "42", "message_id": "m1"}
        prepared = PreparedMessage(
            target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
            payload={
                "text": "first",
                "message_id": "m1",
                "session_id": "qq:private:42",
                "metadata": {"source": "onebot_message_event", "is_owner_user": True},
            },
            route="chat",
        )
        prepared = gateway._annotate_prepared_reception(
            prepared,
            event,
            arrival_seq=1,
            session_queue_key="private:42",
        )
        gateway._mark_latest_session_arrival("private:42", 2)

        await gateway._dispatch_prepared_message(None, prepared, event=event)

        assert gateway.replies == []
        assert any(item["stage"] == "stale_reply_dropped" for item in gateway.traces)
        stale = [item for item in gateway.traces if item["stage"] == "stale_reply_dropped"][-1]
        assert stale["drop_reason"].startswith("newer_input_before_visible_send:1->2")

    asyncio.run(_run())
