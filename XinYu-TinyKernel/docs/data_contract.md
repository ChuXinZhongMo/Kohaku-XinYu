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

## Required Sanitization

- replace local absolute paths with placeholders
- replace IDs with placeholders
- remove secrets and tokens
- reject rows that leak internal tool syntax or state filenames
- reject rows with empty or low-value assistant replies
