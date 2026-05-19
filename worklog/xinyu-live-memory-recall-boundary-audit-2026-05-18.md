# Live Memory Recall Boundary Audit

This report checks that live memory recall has one public owner and that old recall code is only used as a provider/compatibility layer.

- status: pass
- canonical_owner: `xinyu_living_memory_recall.run_living_memory_recall_algorithm`
- provider_module: `xinyu_context_retrieval`
- provider_role: provider/compatibility
- privacy_note: Scans Python source paths/imports only; does not read memory, runtime, QQ payloads, tokens, or private data bodies.

## Provider Importers Outside Owner

- none

## Canonical Importers

- `xinyu_chat_replay_fixture_exporter`
- `xinyu_core_bridge`

## Runtime Entrypoints

### run_living_memory_recall_algorithm
- `xinyu_context_retrieval.py:34`
- `xinyu_contextual_recall.py:19`
- `xinyu_contextual_recall.py:28`
- `xinyu_contextual_self_loop.py:17`
- `xinyu_contextual_self_observatory.py:18`
- `xinyu_contextual_self_replay.py:33`
- `xinyu_conversation_experience_matcher.py:17`
- `xinyu_conversation_experience_sidecar.py:14`
- `xinyu_core_bridge.py:163`
- `xinyu_core_bridge.py:4590`
- `xinyu_living_memory_recall.py:13`
- `xinyu_living_memory_recall.py:76`
- `xinyu_living_memory_recall.py:108`
- `xinyu_living_memory_recall.py:152`
- `xinyu_runtime_context.py:26`

### retrieve_living_memory
- `xinyu_chat_replay_fixture_exporter.py:346`
- `xinyu_chat_replay_fixture_exporter.py:364`
- `xinyu_living_memory_recall.py:93`
- `xinyu_living_memory_recall.py:124`
- `xinyu_living_memory_recall.py:144`
- `xinyu_living_memory_recall.py:162`
- `xinyu_living_memory_recall.py:219`

### build_renderer_memory_context
- `xinyu_answer_discipline_trial.py:20`
- `xinyu_answer_discipline_trial.py:218`
- `xinyu_answer_discipline_trial.py:273`
- `xinyu_answer_discipline_trial.py:327`
- `xinyu_bridge_renderer.py:8`
- `xinyu_bridge_renderer.py:216`
- `xinyu_runtime_context.py:24`
- `xinyu_runtime_context.py:278`
