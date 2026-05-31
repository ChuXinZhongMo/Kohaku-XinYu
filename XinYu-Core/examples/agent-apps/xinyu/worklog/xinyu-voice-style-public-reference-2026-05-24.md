# XinYu Voice Style Public Reference Worklog — 2026-05-24

## Goal

Owner said the proactive examples still did not sound like real people and asked to learn from major video sites and forums instead of hand-writing imagined phrases.

## Public references used

- Chinese-Dialogue-Dataset: open Chinese dialogue dataset index including NaturalConv, LCCC, Douban and related short-dialogue sources.
- CDial-GPT / LCCC: public Chinese short-text conversation corpus/model documentation with Weibo/Tieba/Douban-style dialogue examples.
- DDmkTCCorpus: Bilibili danmaku short-text corpus reference.
- bilibili_comments_crawl: public Bilibili comment-thread crawl project and example conversation snippets.

## Implemented

- Added `xinyu_voice_style_observations.py`.
  - Stores public reference source metadata.
  - Keeps a small public example set only for aggregate style analysis.
  - Exposes `proactive_style_guard()` to reject customer-service/system templates.
  - Exposes shared contextual topic rewrites used by visible proactive speech.
- Generated `memory/self/voice_style_observations.md`.
  - `stable_persona_write: blocked`
  - `owner_memory_write: blocked`
  - `raw_private_body_retained: false`
  - Records aggregate style signals and rewrite rules.
- Updated `xinyu_visible_persona_voice.py`.
  - Proactive questions now prefer short context-reliant replies.
  - Removed long fallback forms that pasted the original engineering question after `我卡在这句` / `这个还接吗：`.
  - Uses shared topic rewrites such as `那几句`, `刚才那条链`, `表现那块`, `Desktop 那张卡`, `QQ 那条`.
- Added `tests/test_voice_style_observations.py`.
- Updated proactive/life-event tests to expect compressed owner-private visible text instead of raw engineering phrases.

## Sample outputs after this round

- `要不要我现在跑一遍生活事件到主动消息的闭环？` -> `刚才那条链要不要接着弄`
- `要不要我先把这些主动消息的句子改得更像平时说话？` -> `那几句还接吗`
- `要不要我先把人格状态卡接到 Desktop？` -> `Desktop 那张卡我继续吗`
- `要不要我先把表达层契约接上？` -> `表现那块还接吗`
- `要不要我把刚才的生活事件链路接到主动直发？` -> `刚才那个还弄吗`
- `当前检测到主动直发检查结果是否需要我继续处理？` -> `这个还接吗`

## Verification

```powershell
python -m pytest tests/test_voice_style_observations.py tests/test_visible_persona_voice.py tests/test_proactive_direct_sender.py tests/test_life_event_runtime.py tests/test_humanlike_life_loop.py -q
```

Result:

```text
17 passed in 0.90s
```

## Boundaries kept

- No stable persona write.
- No owner memory write.
- No raw private body retained.
- No group proactive send.
- No new device/screen/mic/web runtime integration.
- Public examples are used to derive style constraints only; XinYu should not copy public users' personal wording into owner-private messages.

## Follow-up after owner feedback

Owner pointed out that the reference material still looked too thin to count as real collection/learning. I expanded the observation layer from a small sample list to include corpus-level findings:

- NaturalConv: 19.9K conversations / 400K utterances / avg 20.1 turns.
- LCCC-base: 3,354,232 single-turn + 3,466,274 multi-turn sessions; avg 6.79/8.32 words per utterance.
- LCCC-large: 7,273,804 single-turn + 4,733,955 multi-turn sessions; avg 7.45/8.14 words per utterance.
- Tieba Corpus in LCCC: 2.32M sessions.
- Douban Conversation Corpus in LCCC: 0.5M sessions.
- DDmkTCCorpus: 2017-2020 Bilibili videos over 1M views; danmaku text corpus.
- bilibili_comments_crawl: comment-tree paths with minimum dialog length filtering.

Updated aggregate sample observations:

- example_count: 95
- corpus_finding_count: 7
- average_visible_chars: 9.67
- short_reply_count: 50
- medium_reply_count: 38
- long_reply_count: 7
- question_like_count: 9
- first_person_start_count: 12
- particle_ending_count: 28

Verification after expansion:

```powershell
python -m pytest tests/test_voice_style_observations.py tests/test_visible_persona_voice.py tests/test_proactive_direct_sender.py tests/test_life_event_runtime.py tests/test_humanlike_life_loop.py -q
```

Result:

```text
17 passed in 0.96s
```

## Sampler pass

After owner said to start, I added `xinyu_voice_style_sampler.py` and generated `memory/self/voice_style_sample_report.md`.

The sampler does not train on private content. It takes the public reference examples, filters unsafe/private-looking text, tags short-dialogue features, and derives proactive constraints.

Current sample report:

- sample_count: 95
- length_buckets: {"long": 9, "medium": 42, "short": 44}
- short_ratio: 0.463
- contextual_ratio: 0.347
- question_like_count: 21
- first_person_start_count: 12
- deictic_marker_count: 21
- continuation_marker_count: 21
- particle_ending_count: 27
- scene_counts: 接上文/考古 18, 确认/追问 15, 继续/收束 14, 惊讶/吐槽 10, 附和/同感 9

Derived constraints now include:

- 主动消息默认短句；优先 4-14 个可见字，超过 24 字要有明确原因。
- 能指回上下文时，用“刚才那个/那块/那条/那几句”压缩，不复述完整工程名。
- 问句可以不完整，但必须能被最近上下文解释。
- 避免连续第一人称开头；真实短回复里第一人称不是默认入口。
- 可以用轻量语气词收尾，但不要把公网评论腔照搬成卖萌。
- 拒绝客服/系统词：请确认、当前检测到、是否需要我、我将为你。

Verification after sampler:

```powershell
python -m pytest tests/test_voice_style_sampler.py tests/test_voice_style_observations.py tests/test_visible_persona_voice.py tests/test_proactive_direct_sender.py tests/test_life_event_runtime.py tests/test_humanlike_life_loop.py -q
```

Result:

```text
20 passed in 0.86s
```

## Scene-template integration pass

I connected the sampler to proactive visible speech instead of leaving it as a report only.

Implemented:

- `xinyu_voice_style_sampler.py` now exposes `infer_proactive_scene()` and `proactive_scene_templates()`.
- `xinyu_visible_persona_voice.py` now chooses proactive replies through sampler-derived scenes:
  - 接上文/考古
  - 确认/追问
  - 继续/收束
  - 附和/同感
  - 不打扰
- Added tests for scene template selection.

Sample outputs after integration:

- `要不要我现在跑一遍生活事件到主动消息的闭环？` -> `那我接着？`
- `要不要我先把这些主动消息的句子改得更像平时说话？` -> `那几句还要吗`
- `要不要我先把人格状态卡接到 Desktop？` -> `Desktop 那张卡还看吗`
- `要不要我先把表达层契约接上？` -> `表现那块我接着？`
- `那我先不打扰你，晚点再接？` -> `我先收着`

Verification after integration:

```powershell
python -m pytest tests/test_voice_style_sampler.py tests/test_voice_style_observations.py tests/test_visible_persona_voice.py tests/test_proactive_direct_sender.py tests/test_life_event_runtime.py tests/test_humanlike_life_loop.py -q
```

Result:

```text
21 passed in 0.79s
```

## Context-window grounding pass

I added a recent-context path so proactive short replies are not selected only from the current question.

Implemented:

- `compose_proactive_visible_message(..., recent_context=...)` now accepts a small recent context window.
- The context window is scrubbed and drops control lines such as `request_id`, `status`, `trace`, `report`, `outbox`, `batch`, and `source`.
- If the current question is too generic, such as `要不要继续？`, topic compression can use the recent context instead.
- `xinyu_proactive_direct_sender.py` now passes context from `self_thought_state.md` fields:
  - `focus_label`
  - `evidence_label`
  - `why_now`
  - `after_owner_replies`
- Desktop/bridge proactive previews and QQ claim paths now pass available focus/evidence/reason context into the same composer.

Sample outputs after context grounding:

- `要不要继续？` + `主人刚说表达层那块怪，想让我先接表达层契约` -> `表现那块我接着？`
- `要不要继续？` + `request_id/status + 主动消息的句子改得更像平时说话` -> `那几句继续吗`
- `要不要我先把人格状态卡接到 Desktop？` + direct-send context -> `Desktop 那张卡还要吗`
- `要不要我把刚才的生活事件链路接到主动直发？` + life-event context -> `刚才那条链还看吗`

Verification after context grounding:

```powershell
python -m pytest tests/test_voice_style_sampler.py tests/test_voice_style_observations.py tests/test_visible_persona_voice.py tests/test_proactive_direct_sender.py tests/test_life_event_runtime.py tests/test_humanlike_life_loop.py -q
```

Result:

```text
23 passed in 1.41s
```

## Real owner-private turn context pass

I extended the recent-context path beyond self-thought fields so proactive short replies can use the last owner-private turns when available.

Implemented:

- `compose_proactive_visible_message(..., recent_context=...)` now accepts a list of recent turn dicts as well as text.
- Turn dicts are used only when they look owner-private:
  - `sessionKind` is `desktop_private`, `qq_private`, or `owner_private`
  - no group id is present
  - `isOwner` is not explicitly false
  - group-context rows are ignored
- The composer extracts bounded `owner:` / `xinyu:` previews from recent turns and keeps control-line filtering/sensitive scrubbing.
- Topic selection now scores context lines so real owner/xinyu turn text beats low-signal lifecycle fields such as `after_owner_replies`.
- `xinyu_proactive_direct_sender.py` now tries `memory/context/interaction_journal.jsonl` owner-private rows before falling back to `recent_context.md` summary.
- Desktop proactive preview/approve and proactive QQ claim paths now pass runtime owner-private recent turns when present.

Sample outputs after owner-private turn grounding:

- `要不要继续？` + owner-private turn `表达层契约这里先接上 / 我先看表现那块` -> `表现那块继续吗`
- `要不要继续？` + lifecycle fields plus `owner: 表达层契约这里先接上` -> `表现那块我接着？`
- `要不要我把刚才的生活事件链路接到主动直发？` + noisy life-event fields -> `刚才那条链还要吗`

Verification after owner-private turn grounding:

```powershell
python -m pytest tests/test_voice_style_sampler.py tests/test_voice_style_observations.py tests/test_visible_persona_voice.py tests/test_proactive_direct_sender.py tests/test_life_event_runtime.py tests/test_humanlike_life_loop.py -q
```

Result:

```text
26 passed in 1.17s
```

## Recent-context adapter pass

I pulled the owner-private grounding rules into `xinyu_proactive_context_adapter.py` so Desktop preview, Desktop approve, QQ claim, direct sender, and the visible composer all share the same adapter instead of each endpoint hand-parsing recent turns.

Implemented:

- `normalize_proactive_recent_context(...)` for converting text or turn dict lists into the bounded proactive context window.
- `looks_like_owner_private_turn(...)` for one shared owner-private/privacy/group filter.
- `read_recent_owner_private_context(...)` for journal-first direct-send context with `recent_context.md` fallback.
- `runtime_owner_private_turns(...)` for bridge runtime turn-buffer extraction.
- Shared low-signal/context scoring helpers used by `compose_proactive_visible_message`.
- `xinyu_core_bridge.py`, Desktop proactive approve, proactive delivery routes, and direct sender now all call the shared adapter.

Sample after adapter unification:

```text
owner: 主动消息那几句太硬
xinyu: 我改短一点
owner: 表达层契约这里先接上
xinyu: 我先看表现那块
要不要继续？ -> 那我接着？
```

Verification after adapter unification:

```powershell
python -m pytest tests/test_voice_style_sampler.py tests/test_voice_style_observations.py tests/test_proactive_context_adapter.py tests/test_visible_persona_voice.py tests/test_proactive_direct_sender.py tests/test_life_event_runtime.py tests/test_humanlike_life_loop.py -q
```

Result:

```text
30 passed in 1.15s
```

## Remaining risk

This is still not a live crawler and does not download full corpora. It now records broader public corpus-level evidence, a larger example set, a deterministic sampler/report, sampler-derived proactive scene templates, a bounded recent-context path, owner-private recent-turn grounding, and a shared recent-context adapter. True humanlike phrasing will still need more observed public short-dialogue patterns and tests with real archived owner-private turn shapes from the running bridge, not just synthetic journal/turn-buffer examples.
