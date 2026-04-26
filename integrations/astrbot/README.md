# XinYu AstrBot Integration

This directory contains XinYu's AstrBot shell integration.

The shell is deliberately thin. It does not own XinYu's personality, memory,
reflection, source learning, dreams, or growth gates. It only adapts QQ platform
events to the local XinYu core bridge and sends approved replies back through
AstrBot / NapCat.

## Layout

```text
integrations/astrbot/
  plugins/xinyu_bridge/      AstrBot plugin source
  scripts/install_plugin.ps1 Copy plugin into a local AstrBot runtime
  scripts/start_astrbot.ps1  Start the local AstrBot runtime
  scripts/stop_astrbot.ps1   Stop the local AstrBot runtime
  tools/mock_xinyu_bridge.py Mock bridge for shell-only testing
  tools/xinyu_bridge_proactive_smoke.py
  docs/bridge-contract.md    HTTP contract expected by the plugin
  docs/boundaries.md         Shell/core responsibility boundary
```

## Runtime Architecture

```text
QQ
  -> NapCat / OneBot
  -> AstrBot
  -> xinyu_bridge plugin
  -> local XinYu core bridge
  -> XinYu runtime and memory gates
```

## Install Into Local AstrBot

Example local AstrBot root:

```text
D:\XinYu\AstrBot
```

Install the plugin:

```powershell
cd D:\XinYu\KohakuTerrarium-main\integrations\astrbot
.\scripts\install_plugin.ps1 -AstrBotRoot D:\XinYu\AstrBot
```

The script copies:

```text
plugins/xinyu_bridge -> D:\XinYu\AstrBot\data\plugins\xinyu_bridge
```

Start or stop AstrBot:

```powershell
.\scripts\start_astrbot.ps1 -AstrBotRoot D:\XinYu\AstrBot
.\scripts\stop_astrbot.ps1 -AstrBotRoot D:\XinYu\AstrBot
```

## Minimum Plugin Config

Configure in AstrBot's plugin UI or edit AstrBot's generated plugin config:

```json
{
  "enabled": true,
  "bridge_url": "http://127.0.0.1:8765/chat",
  "require_whitelist": true,
  "private_only": true,
  "allow_group_messages": false,
  "stop_astrbot_pipeline": true
}
```

For proactive private QQ delivery:

```json
{
  "proactive_enabled": true,
  "proactive_target_session": "platform-id:FriendMessage:user-id",
  "proactive_poll_seconds": 300,
  "proactive_min_interval_seconds": 21600
}
```

If `proactive_target_session` is empty, the plugin can learn the owner's private
session from a private owner message, or infer it when there is exactly one
platform and one owner id.

## Smoke Test

Test shell plumbing with the mock bridge:

```powershell
python .\tools\mock_xinyu_bridge.py --host 127.0.0.1 --port 8765
```

Then set plugin `bridge_url` to:

```text
http://127.0.0.1:8765/chat
```

Run the proactive shell smoke with the AstrBot Python environment when
available:

```powershell
D:\XinYu\AstrBot\.venv\Scripts\python.exe .\tools\xinyu_bridge_proactive_smoke.py
```

## Status Commands

Send these commands to AstrBot:

```text
/xinyu_shell_status
/xinyu_proactive_once
```

## Privacy Boundary

Do not commit local AstrBot runtime data, generated plugin config, logs,
sessions, caches, or credentials. This directory should contain source and
operator tools only.
