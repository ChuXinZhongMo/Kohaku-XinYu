# TinyKernel API Contract

## `GET /health`

Returns local service readiness.

```json
{
  "ok": true,
  "kernel": "rule",
  "model_loaded": false,
  "adapter": "none"
}
```

## `POST /decide`

Request:

```json
{
  "turn_id": "turn-xxx",
  "source": "owner_private",
  "user_text": "用 Codex 看看这个项目",
  "context": {
    "recent_turns": [],
    "persona_state": "",
    "owner_profile": "",
    "runtime_state": "",
    "memory_recall": []
  },
  "capabilities": {
    "codex_available": true,
    "external_api_available": false,
    "local_tools_available": true
  },
  "constraints": {
    "max_reply_chars": 240,
    "allow_tool_request": true,
    "allow_memory_candidate": true
  }
}
```

Response:

```json
{
  "decision_id": "decision-xxx",
  "mode": "codex_delegate",
  "reply": "",
  "tool_request": {
    "tool": "codex_delegate",
    "risk": "delegated_local",
    "task": "用 Codex 看看这个项目"
  },
  "memory_candidates": [],
  "style": {
    "length": "short",
    "tone": "direct",
    "avoid": ["report_voice", "tool_leak"]
  },
  "confidence": 0.9,
  "notes": ["rule_kernel"]
}
```

## `POST /feedback`

Stores reviewed feedback for future training rows. It does not retrain automatically.

