# NapCat ↔ XinYu QQ gateway (outbox delivery)

Status: active 2026-07-13  
Audience: owner machine operator  
Related: `start_xinyu_qq_gateway.ps1`, `xinyu_qq_gateway.config.json`, private-ecosystem share outbox

## Goal

Deliver owner-private QQ outbox messages (including private-ecosystem browse shares) through:

```text
core bridge :8765  →  qq outbox queue  →  xinyu_qq_gateway :6199/ws  ←  NapCat reverse WS  →  QQ
```

## Required processes

| Process | Port / URL | How |
|---------|------------|-----|
| Core bridge | `http://127.0.0.1:8765` | `start_xinyu_core_bridge.ps1` |
| QQ gateway | `ws://127.0.0.1:6199/ws` | `start_xinyu_qq_gateway.ps1` |
| NapCat / OneBot | reverse **client** to gateway | NapCat Shell + account config |

Gateway alone **listening** is not enough. You need **Established** connections on `6199` (NapCat connected).

## NapCat config (already used on this machine)

File (account-specific):

`runtime/deps/NapCatQQ/NapCat.44498.Shell/versions/9.9.26-44498/resources/app/napcat/config/onebot11_2731787781.json`

Relevant fragment:

```json
"websocketClients": [
  {
    "enable": true,
    "url": "ws://127.0.0.1:6199/ws",
    "name": "xinyu_native_gateway",
    "reconnectInterval": 5000
  }
]
```

Keep this URL aligned with `start_xinyu_qq_gateway.ps1` default port **6199**.

## Operator checklist

Preferred one-shot:

```powershell
.\XinYu.ps1 start qq
.\XinYu.ps1 health
# or: .\scripts\Test-XinYu-StackHealth.ps1 -Strict
```

Manual:

1. Start **core bridge** (`8765` health 200).
2. Start **QQ gateway** (`6199` Listen).
3. Start **NapCat Shell** for the bot account so it opens the reverse WS client.
4. Verify: `Get-NetTCPConnection -LocalPort 6199 -State Established` count **> 0**.
5. Confirm outbox item for PE share leaves `queued`/`claimed` → **`sent`** with `adapter_message_id`.
6. Confirm owner QQ receives the text (e.g. browse observation about GitHub).

## Common failures

| Symptom | Cause |
|---------|--------|
| Outbox stuck `queued` | NapCat not running or WS URL wrong |
| Outbox stuck `claimed` | Manual claim / dead claim without ack; wait claim timeout or requeue |
| `engine: live` but no QQ share | Share path OK; still blocked on NapCat delivery |
| Two gateway pythons on 6199 | Prefer single process; restart gateway cleanly |

## Security

- Do not commit NapCat account configs or tokens.
- `bridge_token` for gateway↔core must match if set; empty config token relies on start-script resolution from `.xinyu_bridge_token` / env.
