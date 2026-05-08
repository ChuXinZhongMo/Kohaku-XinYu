from __future__ import annotations

import asyncio
import time
from typing import Any

from xinyu_qq_outbox_client import GATEWAY_NAME


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


async def gateway_poll_qq_outbox(gateway: Any, websocket: Any, connection_id: str) -> None:
    await poll_qq_outbox(gateway, websocket, connection_id, gateway_name=GATEWAY_NAME)


async def poll_qq_outbox(gateway: Any, websocket: Any, connection_id: str, *, gateway_name: str) -> None:
    await asyncio.sleep(1)
    while True:
        try:
            claim_id = f"{connection_id}-{int(time.time() * 1000)}"
            claim = await gateway.client.qq_outbox_claim(
                {
                    "claim_id": claim_id,
                    "adapter": gateway_name,
                }
            )
            if not claim.get("message_claimed"):
                await asyncio.sleep(gateway.config.qq_outbox_poll_seconds)
                continue

            target = gateway._outbox_target(claim)
            message_type = _safe_str(claim.get("message_type"), "").strip().lower()
            image_path = _safe_str(claim.get("image_path")).strip()
            file_path = _safe_str(claim.get("file_path")).strip()
            file_name = _safe_str(claim.get("file_name")).strip()
            message = gateway._visible_reply(_safe_str(claim.get("message"), ""))
            if target is None:
                await gateway._ack_qq_outbox(
                    claim,
                    status="failed",
                    error="invalid target",
                )
                continue

            if image_path or message_type == "image":
                if not gateway.config.qq_outbox_image_enabled:
                    await gateway._ack_qq_outbox(claim, status="failed", error="qq outbox image dispatch disabled")
                    continue
                image_file, image_error = gateway._onebot_local_image_file(image_path)
                if image_error:
                    await gateway._ack_qq_outbox(claim, status="failed", error=image_error)
                    continue
                action_response = await gateway.send_image(websocket, target, image_file)
                ok, adapter_message_id, adapter_error = gateway._onebot_action_result(action_response)
                if ok and adapter_message_id:
                    await gateway._ack_sent_outbox_delivery(
                        claim,
                        target=target,
                        visible_text="",
                        adapter_message_id=adapter_message_id,
                        delivery_kind="image",
                        adapter_error=adapter_error,
                    )
                if ok and message:
                    caption_response = await gateway.send_reply(websocket, target, message)
                    caption_ok, caption_message_id, caption_error = gateway._onebot_action_result(caption_response)
                    if caption_ok and caption_message_id:
                        await gateway._ack_sent_outbox_delivery(
                            claim,
                            target=target,
                            visible_text=message,
                            adapter_message_id=caption_message_id,
                            delivery_kind="caption",
                            adapter_error=caption_error,
                        )
                        adapter_message_id = ",".join(part for part in (adapter_message_id, caption_message_id) if part)
                    elif not caption_ok:
                        adapter_error = f"caption_send_failed:{caption_error or 'unknown'}"
                await gateway._ack_qq_outbox(
                    claim,
                    status="sent" if ok else "failed",
                    adapter_message_id=adapter_message_id,
                    error=adapter_error,
                )
                continue
            if file_path or message_type == "file":
                if not gateway.config.qq_outbox_file_enabled:
                    await gateway._ack_qq_outbox(claim, status="failed", error="qq outbox file dispatch disabled")
                    continue
                local_file, local_name, file_error = gateway._onebot_local_file(file_path, file_name=file_name)
                if file_error:
                    await gateway._ack_qq_outbox(claim, status="failed", error=file_error)
                    continue
                action_response = await gateway.send_file(websocket, target, local_file, name=local_name)
            else:
                if not message:
                    await gateway._ack_qq_outbox(claim, status="failed", error="empty text message")
                    continue
                bubbles = gateway._outbox_visible_reply_bubbles(target, message, claim)
                responses: list[dict[str, Any] | None] = []
                for index, bubble in enumerate(bubbles):
                    if index > 0:
                        delay = max(0.0, gateway.config.reply_bubble_delay_seconds)
                        if delay:
                            await asyncio.sleep(delay)
                    responses.append(await gateway.send_reply(websocket, target, bubble))
                action_response = gateway._combined_reply_action_response(responses)
            ok, adapter_message_id, adapter_error = gateway._onebot_action_result(action_response)
            if ok and adapter_message_id and not (file_path or message_type == "file"):
                await gateway._ack_sent_outbox_delivery(
                    claim,
                    target=target,
                    visible_text=message,
                    adapter_message_id=adapter_message_id,
                    delivery_kind=message_type or "text",
                    adapter_error=adapter_error,
                )
            await gateway._ack_qq_outbox(
                claim,
                status="sent" if ok else "failed",
                adapter_message_id=adapter_message_id,
                error=adapter_error,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[xinyu_qq_gateway] QQ outbox poll error: {type(exc).__name__}: {exc}", flush=True)
            await asyncio.sleep(max(5, gateway.config.qq_outbox_poll_seconds))
