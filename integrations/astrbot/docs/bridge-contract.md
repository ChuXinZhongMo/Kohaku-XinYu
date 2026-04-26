# XinYu Bridge Contract

The AstrBot shell plugin expects a local HTTP endpoint owned by the XinYu core.
The shell does not implement XinYu memory or reasoning.

Default chat endpoint:

```text
POST http://127.0.0.1:8765/chat
```

## Request

```json
{
  "platform": "astrbot",
  "message_type": "private_text",
  "session_id": "astrbot:private:123456",
  "user_id": "123456",
  "sender_name": "owner",
  "group_id": null,
  "bot_id": "bot",
  "message_id": "message-id",
  "text": "hello",
  "raw_message": "hello",
  "metadata": {
    "unified_msg_origin": "...",
    "platform_session_id": "...",
    "plugin": "xinyu_bridge",
    "shell_version": "0.3.0"
  }
}
```

## Response

```json
{
  "accepted": true,
  "reply": "XinYu reply text",
  "memory_changed": false,
  "notes": []
}
```

Fields:

- `accepted`: whether XinYu accepted the event.
- `reply`: plain text sent back by AstrBot. Empty reply means no platform output.
- `memory_changed`: optional diagnostic value for logging.
- `notes`: optional diagnostic strings. They are logged by the shell and not sent
  to ordinary users.

## Authentication

If `bridge_token` is configured in the AstrBot plugin, the plugin sends both:

```text
Authorization: Bearer <token>
X-XinYu-Bridge-Token: <token>
```

The core endpoint should reject mismatched tokens when a token is configured.

## File Learning Ingest

The shell sends QQ file attachments to:

```text
POST http://127.0.0.1:8765/learning/ingest
```

Request:

```json
{
  "platform": "astrbot",
  "source": "astrbot_file_message",
  "origin": "owner_supplied",
  "file_name": "心玉人格记忆.docx",
  "file_path": "C:\\Users\\26921\\Desktop\\心玉人格记忆.docx",
  "file_url": "",
  "reason": "QQ file attachment from owner",
  "question_id": "qq-file-learning",
  "stage": true,
  "curated": true,
  "max_bytes": 52428800,
  "metadata": {
    "plugin": "xinyu_bridge",
    "shell_version": "0.3.0",
    "message_type": "private_file"
  }
}
```

Response:

```json
{
  "accepted": true,
  "reply": "收到了：心玉人格记忆.docx。已经放进学习资料库，并登记到学习管道，已提取可阅读文本。",
  "learning_item_id": "learn-...",
  "material_id": "material-...",
  "extracted_text": true,
  "notes": ["learning_ingest", "no_agent_turn"]
}
```

The shell does not parse or learn the file itself. The core copies the file into
the learning library, extracts readable text when supported, and stages owner
material into the source-material pipeline.

Supported readable formats currently include `.md`, `.txt`, `.docx`, text
`.pdf`, scanned PDF OCR, image OCR, `.pptx`, `.xlsx`, `.rtf`, `.odt`, common
code files, and common markup files. OCR uses Windows OCR when available, or
`XINYU_OCR_COMMAND` / Tesseract when configured. Legacy `.doc`, `.ppt`, `.xls`
are accepted as source files but still need conversion before text extraction.

## Proactive Delivery

The shell may poll:

```text
POST http://127.0.0.1:8765/proactive
```

Request:

```json
{
  "claim": true,
  "claim_id": "astrbot-1777210000",
  "min_interval_seconds": 21600,
  "source": "background_loop"
}
```

If XinYu has a gated outbound candidate, the core returns `reply` and the same
or replacement `claim_id`. The shell sends `reply` to the configured owner
private session, then calls:

```text
POST http://127.0.0.1:8765/proactive/ack
```

Success:

```json
{
  "claim_id": "astrbot-1777210000",
  "status": "sent",
  "message_id": "astrbot:platform-id:FriendMessage:user-id:1777210001"
}
```

Failure:

```json
{
  "claim_id": "astrbot-1777210000",
  "status": "failed",
  "error": "target session not found"
}
```

The shell never fabricates proactive content. It only sends text already
approved and claimed by the XinYu core.

## Error Behavior

The plugin treats network errors, non-2xx responses, and invalid JSON as bridge
failures. During testing, set `show_bridge_errors` to `true`; for live use,
prefer `false` and inspect AstrBot logs.
