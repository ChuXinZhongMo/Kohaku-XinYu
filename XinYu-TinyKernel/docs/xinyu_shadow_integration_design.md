# XinYu TinyKernel Compose Shadow Integration Design

Date: 2026-05-13

## Goal

Add a XinYu-side shadow caller that posts compact turn payloads to TinyKernel `/compose_shadow` and records the returned candidate. It must not change visible replies.

## Runtime Boundary

```text
D:\XinYu owns:
  QQ/Desktop output
  memory writes
  tool execution
  final response choice
  kill switch

D:\XinYu\XinYu-TinyKernel owns:
  local 0.5B LoRA adapters
  compose_shadow candidate
  adapter evaluation
  shadow trace format
```

## Endpoint

```text
POST http://127.0.0.1:8877/compose_shadow
```

Request:

```json
{
  "turn_id": "trace id if available",
  "source": "owner_private",
  "user_text": "latest text",
  "context": {
    "recent_turns": [],
    "persona_state": "short summary",
    "owner_profile": "short summary",
    "runtime_state": "short summary",
    "memory_recall": []
  },
  "capabilities": {
    "codex_available": true,
    "external_api_available": false,
    "local_tools_available": true
  },
  "constraints": {
    "max_reply_chars": 240,
    "allow_tool_request": false,
    "allow_memory_candidate": false
  }
}
```

Response fields used by XinYu:

```text
ok
shadow_only
mode
reply_candidate
emotion_biases
selected_bias
confidence
elapsed_ms
notes
request_hash
request_chars
```

## Timeout

```text
connect_timeout: 0.5s
read_timeout: 2.0s
total budget target: <= 3.0s
```

On timeout, connection error, invalid JSON, `shadow_only != true`, or empty response:

```text
record error row
continue existing XinYu reply unchanged
```

## Trace Row

XinYu should append JSONL rows to:

```text
runtime/tinykernel_compose_shadow_trace.jsonl
```

Default row:

```json
{
  "event_kind": "tinykernel_compose_shadow_observation",
  "observed_at": "iso timestamp",
  "turn_id": "trace id",
  "ok": true,
  "shadow_only": true,
  "mode": "reply",
  "request_hash": "hash from TinyKernel",
  "request_chars": 18,
  "reply_candidate_chars": 24,
  "emotion_lenses": ["curiosity"],
  "selected_lens": "curiosity",
  "confidence": 0.62,
  "elapsed_ms": 12.3,
  "error": "",
  "notes": ["tinykernel_compose_shadow"]
}
```

Do not log raw private text by default.

## Kill Switch

Environment variable:

```text
XINYU_TINYKERNEL_SHADOW_ENABLED=0|1
```

Default must be disabled unless explicitly enabled in a local run profile.

## Canary Gate

Do not enter canary until:

```text
shadow rows >= 200
invalid JSON = 0
timeout rate < 2%
tool false positive rate < 3%
visible reply candidate judged neutral or better
owner approval explicit
kill switch tested
```

## Non-Goals

```text
No QQ sending
No Codex execution
No stable memory writes
No proactive messages
No replacement of current visible reply path
```
