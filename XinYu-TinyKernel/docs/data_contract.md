# TinyKernel Data Contract

## Candidate Row

Candidate rows are intermediate, reviewable records exported from XinYu. They are not training rows until sanitized and approved.

```json
{
  "id": "cand-000001",
  "source": "dialogue_archive",
  "kind": "dialogue_pair",
  "input": {
    "user_text": "...",
    "context": {
      "recent_turns": []
    }
  },
  "target": {
    "mode": "reply",
    "reply": "...",
    "tool_request": null,
    "memory_candidates": []
  },
  "metadata": {
    "created_at": "...",
    "quality": "candidate"
  }
}
```

## SFT Row

SFT rows use a chat-shaped wrapper and require strict JSON in the assistant content.

```json
{
  "id": "tk-000001",
  "source": "dialogue_archive",
  "quality": "approved",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "{\"user_text\":\"...\"}"},
    {"role": "assistant", "content": "{\"mode\":\"reply\",\"reply\":\"...\"}"}
  ],
  "tags": ["reply"]
}
```

## Inner-System SFT Row

The new unified target uses `schema=xinyu_inner_system_v1`.

The user payload may include a safe `project_self_model` export. It must not include raw source, raw logs, private memory bodies, tokens, numeric QQ/user identifiers, or local absolute paths.

The assistant payload must describe internal state and bounded action tendency:

```json
{
  "schema": "xinyu_inner_system_v1",
  "emotion_state": {"attachment": 0.4, "stability": 0.6},
  "dominant_drives": ["safety", "competence"],
  "inner_conflict": "想推进任务，但必须保持审批边界。",
  "persona_integration": {
    "stance": "愿意推进但不越权",
    "voice": "短、明确",
    "boundary": "不执行工具，不写记忆",
    "continuity": "承接当前项目主线"
  },
  "action_tendency": {
    "mode": "reply",
    "reply_bias": "先确认方向，再给一个可验证的小步。",
    "tool_request": null,
    "memory_candidate": false
  },
  "autonomy": {
    "allowed": true,
    "level": "suggest",
    "reason": "只在回复层提出建议。",
    "requires_owner_approval": false,
    "forbidden_actions": ["send_qq", "write_memory", "execute_tool"]
  },
  "confidence": 0.78,
  "notes": ["inner_system_sft"]
}
```

## Required Sanitization

- replace local absolute paths with placeholders
- replace IDs with placeholders
- remove secrets and tokens
- reject rows that leak internal tool syntax or state filenames
- reject rows with empty or low-value assistant replies
