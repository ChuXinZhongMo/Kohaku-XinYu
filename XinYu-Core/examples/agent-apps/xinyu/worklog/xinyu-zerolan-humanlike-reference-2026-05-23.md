# XinYu × ZerolanProject Humanlike Reference Worklog — 2026-05-23

## Repositories reviewed

- ZerolanLiveRobot: event-driven AI VTuber runtime, multimodal input, QQ/NapCat, OBS, Live2D, tools, Minecraft action.
- zerolan-core: unified local model services for LLM, ASR, TTS, OCR, image/video caption, VLA, vector DB, defense.
- zerolan-data: strict Pydantic schemas for pipeline and protocol data.
- ZerolanPlayground: Unity/AR/Live2D expression frontend.

## Reference value for XinYu

The most useful idea is not the VTuber UI itself. It is the separation:

```text
events -> model/service pipelines -> decisions -> expression/action adapters -> feedback
```

For XinYu, this maps to:

```text
life events -> attention/initiative gates -> proactive request/chat/silence/reflection -> QQ/Desktop outbox -> ack/reply feedback -> memory/growth gates
```

## What was written into the project

- Added `project-plans/XINYU-ZEROLAN-HUMANLIKE-REFERENCE-PLAN-2026-05-23.md`.
- Updated `project-plans/README.md` to list it as an active plan.

## Humanlike direction captured

- XinYu should have a continuous life/event stream, not only reply turns.
- She should decide what to notice, ignore, remember, ask, or act on.
- Proactive speech must remain concrete, owner-private, deduped, and gated.
- Frontend/body expression should be an adapter, not the identity layer.
- Model/multimodal services should be capability pipelines, not persona mutations.
- Stable persona, owner relationship memory, and private raw bodies remain protected.

## Next safe implementation step

Implement a small `xinyu_life_event_contract.py` plus tests. It should define sanitized event fields and route decisions only; no device capture, no network, no raw private body, no stable memory write.
