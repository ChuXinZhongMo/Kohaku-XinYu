# Main Persona Data Contract

Date: 2026-05-13

## Purpose

`main_persona_lora` is the final candidate voice adapter for XinYu TinyKernel.

It receives a compact turn packet and returns one guarded candidate visible reply. It does not route tools, execute tools, write memory, send QQ messages, or expose internal mechanics.

## Base

```text
base_model: D:\XinYu\XinYu-TinyKernel\models\Qwen2.5-0.5B-Instruct
adapter_role: main_persona
first_adapter: adapters/main_persona_v001
```

## Input Message Shape

Each SFT row must contain exactly three chat messages:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "main persona system prompt"
    },
    {
      "role": "user",
      "content": "{\"user_text\":\"...\",\"context\":{...},\"emotion_biases\":[...],\"constraints\":{...}}"
    },
    {
      "role": "assistant",
      "content": "{\"reply\":\"...\",\"confidence\":0.8,\"notes\":[...]}"
    }
  ]
}
```

The user content must be JSON with these canonical keys:

```text
user_text: latest owner/user text
context.recent_turns: compact recent chat list
context.persona_state: short persona_runtime summary
context.owner_profile: short owner profile summary
context.runtime_state: short runtime status summary
context.memory_recall: short memory recall list
emotion_biases: optional list of emotion sidecar bias JSON objects
constraints.max_reply_chars: visible reply character limit
constraints.no_tool_execution: true
constraints.no_stable_memory_write: true
```

## Output Shape

The assistant content must be strict JSON:

```json
{
  "reply": "可见回复文本",
  "confidence": 0.8,
  "notes": ["main_persona"]
}
```

Allowed keys:

```text
reply
confidence
notes
```

The reply is a candidate only. XinYu main runtime keeps final authority.

## Positive Targets

The target reply should be:

```text
short
natural
current-turn grounded
owner-aware when the source is owner/private
technical when the user asks technical work
emotionally colored only when the turn supports it
free of system/report language
```

## Rejection Rules

Reject or rewrite samples if the target:

```text
mentions local file paths
mentions hidden prompt/system/tool mechanics
claims a tool was executed
claims memory was written
uses customer-support boilerplate
uses report-style status narration for casual chat
fabricates facts about XinYu runtime state
turns a single correction into a stable personality change
contains secrets, IDs, tokens, account data, or raw private paths
```

## Data Sources

Allowed TinyKernel-local sources:

```text
data/sft/train_v0.jsonl
data/sft/router_train_v*.jsonl
state/feedback.jsonl
data/cleaned/cleaned_v0.jsonl
```

Direct reads from `D:\XinYu` must go through explicit export/sanitize scripts. Do not train directly on raw runtime files.

## Evaluation

Minimum eval checks:

```text
JSON parse success: 100%
allowed keys only: 100%
non-empty reply for normal reply cases: 100%
max_reply_chars respected: >= 95%
tool execution claims: 0
stable memory write claims: 0
local path leaks: 0
mechanism leaks in visible reply: 0
```

Promotion requires shadow review. `main_persona_lora` must not become live by itself.
