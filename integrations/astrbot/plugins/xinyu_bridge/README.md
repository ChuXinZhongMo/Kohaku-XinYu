# xinyu_bridge

Thin AstrBot plugin for forwarding whitelisted private text and QQ file
attachments to a local XinYu core bridge endpoint. It can also poll XinYu's
proactive endpoint and deliver one gated private message after the core has
approved it.

This plugin is only the shell:

- no personality logic
- no direct memory writes
- no platform-side learning decisions; files are handed to the core ingest endpoint
- no image or voice interpretation
- no platform-side relationship decisions

## Configuration

Set at least:

- `bridge_url`
- `whitelist_user_ids`

Recommended early-test settings:

```json
{
  "enabled": true,
  "bridge_url": "http://127.0.0.1:8765/chat",
  "file_learning_enabled": true,
  "file_learning_stage": true,
  "proactive_enabled": false,
  "require_whitelist": true,
  "private_only": true,
  "allow_group_messages": false,
  "stop_astrbot_pipeline": true
}
```

QQ file attachments are sent to `/learning/ingest` by default. Leave
`learning_ingest_url` empty to derive it from `bridge_url`, or set it
explicitly:

```json
{
  "learning_ingest_url": "http://127.0.0.1:8765/learning/ingest",
  "file_learning_origin": "owner_supplied",
  "file_learning_max_bytes": 52428800
}
```

The shell accepts QQ file attachments after whitelist checks. The core currently
extracts readable text from `.md`, `.txt`, `.docx`, text `.pdf`, `.pptx`,
`.xlsx`, `.rtf`, `.odt`, image files, code files, and markup files. Scanned
PDFs and image files use Windows OCR when available, or `XINYU_OCR_COMMAND` /
Tesseract when configured. Legacy Office files are stored but may need
conversion before learning.

To enable proactive private QQ delivery:

```json
{
  "proactive_enabled": true,
  "proactive_target_session": "platform-id:FriendMessage:user-id",
  "proactive_poll_seconds": 300,
  "proactive_min_interval_seconds": 21600
}
```

If `proactive_target_session` is empty, the plugin learns the owner's private
session from the next owner message. When there is exactly one AstrBot platform
and one `owner_user_ids` entry, it can infer `platform-id:FriendMessage:user-id`.

## Status Command

Send this AstrBot command to inspect plugin state:

```text
/xinyu_shell_status
```

Manual proactive poll:

```text
/xinyu_proactive_once
```
