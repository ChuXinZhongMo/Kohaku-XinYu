# XinYu Shadow Integration Plan

This document describes how `D:\XinYu` should call TinyKernel later without changing visible behavior.

Current status:

```text
TinyKernel service: http://127.0.0.1:8877
Integration status: not connected to D:\XinYu
Mode: local shadow sample implemented; XinYu-side shadow not connected
```

## Goal

Add a shadow caller in XinYu Core that posts a compact turn summary to TinyKernel and records the returned decision. The live XinYu reply remains unchanged.

```text
owner turn
-> existing XinYu pipeline produces visible reply
-> shadow caller posts to TinyKernel /decide
-> decision written to runtime/tinykernel_shadow_trace.jsonl
-> no visible effect
```

## Non-Goals

- Do not let TinyKernel send QQ messages.
- Do not let TinyKernel execute tools.
- Do not let TinyKernel write stable memory.
- Do not block live replies on TinyKernel.
- Do not switch to TinyKernel output during shadow.

## Request Shape

```json
{
  "turn_id": "existing-turn-id",
  "source": "owner_private",
  "user_text": "latest owner text",
  "context": {
    "recent_turns": [],
    "persona_state": "short redacted summary",
    "owner_profile": "short redacted summary",
    "runtime_state": "short redacted summary",
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

## Timeout And Fallback

Recommended timeout:

```text
connect_timeout: 0.5s
read_timeout: 2.0s
total budget: <= 3.0s
```

On timeout, connection error, invalid JSON, or invalid mode:

```text
record shadow_error
continue live pipeline unchanged
```

## Trace Row

```json
{
  "event_kind": "tinykernel_shadow_decision",
  "observed_at": "iso timestamp",
  "turn_id": "turn id",
  "source": "owner_private",
  "request_chars": 120,
  "ok": true,
  "mode": "reply",
  "confidence": 0.68,
  "tool": "",
  "memory_candidate_count": 0,
  "elapsed_ms": 42,
  "error": ""
}
```

Do not log full private text by default. Keep full request/response logging behind a local debug flag only.

## Promotion Criteria

Do not enter canary until:

```text
shadow rows >= 200
invalid JSON = 0
timeout rate < 2%
tool false positive rate < 3%
negative tool requests blocked >= 95%
owner-visible style judged better or neutral
```

## Canary Scope

First canary scopes:

```text
memory candidate suggestion
Codex intent suggestion
short low-risk reply suggestion
```

Still blocked:

```text
actual Codex execution
stable memory writes
QQ proactive messages
code changes
```

## Candidate XinYu Files To Inspect Later

Likely integration points, to be confirmed before editing:

```text
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_core_bridge.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_bridge_turn_pipeline.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_bridge_v1_routes.py
```

No edits have been made to those files by TinyKernel work.

## Local Guarded Shadow Sample

TinyKernel now has a local-only shadow sampler that does not modify `D:\XinYu`:

```powershell
cd D:\XinYu\XinYu-TinyKernel
$env:HF_ENDPOINT='https://hf-mirror.com'
.\.venv-train\Scripts\python.exe scripts\shadow_guarded_sample.py --adapter adapters\v004_router_edges --out state\shadow_guarded_trace.jsonl
```

Latest local sample:

```text
rows_written=10
disagreement_count=0
model_call_count=1
out=state\shadow_guarded_trace.jsonl
```

The script logs hashes and mode summaries by default, not raw private text.
