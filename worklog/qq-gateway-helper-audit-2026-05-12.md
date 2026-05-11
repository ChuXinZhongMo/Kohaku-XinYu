# QQ Gateway Helper Audit - 2026-05-12

## Scope

Audit remaining `NativeQQGateway` private helpers after Loop 145.

Goal: choose safe, reversible extraction slices without widening QQ behavior, prompt/persona behavior, or v1 traffic.

## Current Shape

`xinyu_qq_gateway.py` already delegates many pure responsibilities through direct aliases:

- Trust policy: `xinyu_qq_trust_policy.py`
- Outbox client/dispatcher: `xinyu_qq_outbox_client.py`, `xinyu_qq_outbox_dispatcher.py`
- Attachment/media resolution: `xinyu_qq_attachment_resolver.py`
- CQ/OneBot normalization: `xinyu_qq_normalizer.py`
- Forward context parsing: `xinyu_qq_forward_context.py`
- Rich context summary: `xinyu_qq_rich_context.py`
- Sticker semantics: `xinyu_qq_sticker_semantics.py`
- Reply bubble helpers: `xinyu_qq_reply_bubbles.py`

The remaining methods fall into three groups.

## Safe Near-Term Candidates

- `_visible_reply_bubbles`
  - Owner module: `xinyu_qq_reply_bubbles.py`
  - Reason: pure orchestration over forced units, split gate, and chunking.
  - Validation: QQ gateway smoke and QQ review smoke.
- `_outbox_visible_reply_bubbles`
  - Owner module: `xinyu_qq_reply_bubbles.py`
  - Reason: pure outbox variant of reply bubble orchestration.
  - Validation: QQ gateway smoke and QQ review smoke.
- `_combined_reply_action_response`
  - Owner module candidate: `xinyu_qq_outbox_client.py` or reply bubble helper.
  - Reason: pure aggregation of OneBot action responses, but depends on `_onebot_action_result`; extract only after reply bubble wrappers are moved.

## Conditional Candidates

- `_summarize_forward_item`
  - Owner module candidate: `xinyu_qq_forward_context.py`
  - Risk: currently calls gateway rich-context/text helpers; extract only with a small adapter or after richer forward-context helpers exist.
- `_extract_rich_message_context`
  - Owner module candidate: `xinyu_qq_rich_context.py`
  - Risk: uses gateway text/reply/forward aliases and visible fallback strings; extract only with dedicated smoke coverage.
- `_sticker_import_material_from_segment`, `_learning_material_from_segment`, `_learning_material_from_cq`
  - Owner module candidate: `xinyu_qq_attachment_resolver.py`
  - Risk: relies on sticker/image semantic gates; safe later with focused attachment resolver smoke.
- `_learning_reason_text`
  - Owner module candidate: `xinyu_qq_attachment_resolver.py`
  - Risk: low, but visible default text should stay byte-for-byte stable.
- `_sticker_followup_text`, `_first_sticker_import_item`, `_enrich_sticker_segments_with_import_context`
  - Owner module candidate: sticker import/context helper.
  - Risk: mojibake-visible strings and followup semantics; extract only with sticker import smoke.

## Keep In Gateway For Now

- WebSocket lifecycle, pending action futures, arrival/dispatch sequencing.
- Core bridge request routing and control-plane command preparation.
- Recent sticker import background scheduling and runtime state writes.
- Group coalescing and group shadow event recording.
- Payload builders for chat, learning ingest, sticker import, package install, Codex command, Goldmark, and review admin.
- Real send path and ack recording around `send_reply`, `send_action`, and outbox dispatch.

These still combine config, live gateway state, runtime writes, or core bridge protocol assembly. They can be decomposed later, but not as blind helper moves.

## Next Slice

Extract `_visible_reply_bubbles` and `_outbox_visible_reply_bubbles` into `xinyu_qq_reply_bubbles.py` as gateway-bound aliases.

Expected commit:

```text
refactor: extract qq reply bubble orchestration helpers
```
