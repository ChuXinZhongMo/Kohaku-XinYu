# XinYu Persona Realism Smoke Gate - 2026-05-18

Status: complete as persona realism gate integration batch.

## Batch Scope

- Capability group: persona/runtime voice validation.
- Goal: make persona realism evaluation part of regular smoke validation instead of a standalone optional check.
- Privacy boundary: the eval uses synthetic samples only and does not read private chat, raw QQ content, or memory bodies.

## Completed

- Updated `smoke_run.py`.
  - Added `xinyu_persona_realism_eval.py` to the quick `py_compile` set.
  - Added `tests/smoke/voice/persona_realism_eval_smoke.py` to `quick`.
  - Added `tests/smoke/voice/persona_realism_eval_smoke.py` to `voice`.

## Direct Impact

- Persona realism is now a regular gate, not a manual extra.
- Quick smoke now fails if XinYu drifts into:
  - rolecard-style language;
  - false biology claims;
  - internal state leaks;
  - theatrical persona performance;
  - emotion treated as fact;
  - overly long replies;
  - technical work emotionalized;
  - generic tool-flat phrasing.

## Validation

Passed:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe tests\smoke\voice\persona_realism_eval_smoke.py
.\.venv\Scripts\python.exe -m py_compile smoke_run.py xinyu_persona_realism_eval.py tests\smoke\voice\persona_realism_eval_smoke.py
.\.venv\Scripts\python.exe -m pytest tests\test_persona_realism_eval.py -q
.\.venv\Scripts\python.exe smoke_run.py --group voice --restore-after --timeout-seconds 300
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300
```

Results:

- Persona smoke: passed.
- Focused pytest: 4 passed.
- Voice smoke group: passed.
- Quick smoke group: passed and included `persona_realism_eval_smoke.py`.

## Recovery Point

Resume from:

- `smoke_run.py`
- `tests/smoke/voice/persona_realism_eval_smoke.py`
- `xinyu_persona_realism_eval.py`
