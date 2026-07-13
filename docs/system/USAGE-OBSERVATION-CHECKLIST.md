# Usage observation checklist (post-v0.1.0)

Status: active 2026-07-13  
Audience: owner / operator after stack is green  
Related: `docs/system/NAPCAT-GATEWAY-OPERATOR.md`, `scripts/Test-XinYu-StackHealth.ps1`

Use this for **1–2 days of real use**, not for CI. Goal: capture 3 concrete pain points before more engineering.

## 0. Preflight (each session)

```powershell
.\scripts\Test-XinYu-StackHealth.ps1
# if fail:
.\XinYu.ps1 start qq
.\scripts\Test-XinYu-StackHealth.ps1 -Strict
```

Expect: bridge `:8765` ok, gateway `:6199` listen, NapCat **Established > 0**, outbox no stuck backlog.

## 1. Private chat

| Check | Pass? | Notes |
|-------|-------|-------|
| Normal short reply feels non-robotic | | |
| No mechanical “还看吗/还要吗” tics | | |
| Long replies bubble/split acceptably | | |
| Owner commands (trust/mark/etc.) still work | | |

## 2. Voice / TTS

| Check | Pass? | Notes |
|-------|-------|-------|
| Private voice reply enables when intended | | |
| Emotion / delivery not always flat (if `XINYU_TTS_EMOTION=1`) | | |
| Strict voice failure does not silently become wrong text | | |
| Sample rate / “电子音” not back | | |

## 3. Private ecosystem browse → share

| Check | Pass? | Notes |
|-------|-------|-------|
| `browser_state.engine` becomes `live` after browse | | |
| Allowlist stays GitHub-only | | |
| Browse observation can enqueue share | | |
| Share actually **sent** to owner QQ (not stuck queued) | | |
| Quiet hours / cooldown behave as expected | | |

## 4. Reliability

| Check | Pass? | Notes |
|-------|-------|-------|
| After reboot, start order is obvious | | |
| If NapCat dies, health script shows Established=0 | | |
| Outbox backlog clears after reconnect | | |
| Desktop shell can still show PE/status | | |

## 5. Capture template (copy into notes)

```text
Date:
Scenario:
Expected:
Actual:
Logs/state pointers (no secrets):
  - browser_state.engine=
  - outbox status=
  - 6199 Established=
Severity (block/annoy/nit):
```

## 6. When to open engineering work

Open a PR only if pain is **repeatable** and maps to one of:

- delivery/ops (start/health/outbox)
- voice quality/contract
- PE browse/share policy
- gateway/presence modularity blocking a fix

Do **not** open “more CI” or desktop major bumps without a product trigger.
