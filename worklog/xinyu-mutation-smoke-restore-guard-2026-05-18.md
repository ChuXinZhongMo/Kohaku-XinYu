# XinYu Mutation Smoke Restore Guard

Generated from smoke source files only.
It does not read or print memory bodies, QQ payloads, tokens, or secrets.

- total_smokes: 22
- mutation_capable_count: 19
- restore_after_supported_count: 19
- diff_suppression_supported_count: 19
- missing_restore_count: 0
- missing_diff_suppression_count: 0

## Mutation-Capable Smokes

- `tests/smoke/learning/integration/ai_domain_source_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/autonomous_search_activation_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/learner_integration_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/learning_quality_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/learning_session_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/outward_source_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/question_pipeline_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/source_comparison_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/source_learning_chain_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/source_quality_followup_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/source_reliability_gate_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/source_request_planner_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/source_search_provider_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/learning/integration/source_search_resolution_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/memory/integration/archive_commit_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/memory/integration/long_term_memory_gate_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/memory/integration/memory_arc_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=yes | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/memory/integration/memory_mutation_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=yes | recommended=`--restore-after --diff-lines 0`
- `tests/smoke/memory/integration/memory_pressure_smoke.py` | restore_after=yes | diff_lines=yes | default_restore=no | recommended=`--restore-after --diff-lines 0`

## Rule

- Mutation-capable smoke scripts should be run with `--restore-after`.
- When a smoke supports diff rendering, use `--diff-lines 0` during autonomous validation.
