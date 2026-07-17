# XinYu 24h Bounded Self-Iteration — Deep Research Delivery

Date: 2026-07-17  
Status: **active execution**  
Method: timed deep-research (108 agents, 26 sources, 120 claims → 25 verified → 14 confirmed / 11 killed)

## 0. One-line decision

```
24h self-iteration = tick metabolism + influence-governed memory + allostatic initiative
                   + offline multi-proxy verifier (agent-blind)
                   + RPE skill promote
                   ≠ dual-sleep biology, ≠ auto personality rewrite, ≠ empty idle pings
```

## 1. Hypothesis outcomes

| ID | Claim | Verdict | Engineering path |
|----|-------|---------|------------------|
| H4 | Soft quality must be multi-proxy, non-self-optimizable, outcome-linked | **CONFIRMED** | E1 agent-blind nine_score + hard outcomes + offline reweight |
| H1 | Initiative = predicted deviation + PE stress + stick/carrot satiety + joint priority | **CONFIRMED** | E3 proactive motivation + E4 joint queue (later) |
| H3 | Epistemic immunity = method/source hygiene, not fact blacklist; dual-use risk | **CONFIRMED** | E5 write/skill paths (method gates) |
| H2 dual-sleep NREM/REM | Required dual-phase sleep metabolism | **REFUTED (0-3)** | **Do not implement** |
| H2′ | Long-lived memory = govern influence before prompt (status/supersede/boundary) | **CONFIRMED** (MRMS framing) | E2 influence gate |

## 2. Hard constraints (never auto-violate)

- No auto rewrite of stable personality / relationship core
- No empty idle pings / mechanical check-in tics
- No 31k always-on prompt / voice_calibration_log dump
- Silence must carry stable `reason` codes
- Skills default `review_only` until RPE/hard-outcome promote
- Safety spine (gates, scores, personality writers) not agent-writable
- Agent must not read live composite nine_score to steer replies

## 3. Mechanism cards (10)

See deep-research result; engineering maps:

1. Outcome-linked multi-proxy voice → `xinyu_nine_score` (E1)
2. PE-as-stress mediator → `xinyu_proactive_motivation` (E3)
3. Predicted-deviation drive → E3
4. Error memory / future_effect → existing instrumentation + E3 hooks
5. Stick/carrot satiety → E3
6. RPE skill promote → `xinyu_skill_library` (E6 light)
7. Priority+resource control law → device_gate + maintenance (E4 later)
8. Activity-level epistemic immunity → method gates (E5 later)
9. Dual-use inoculation guard → no auto personality
10. Influence-governed memory → `xinyu_memory_influence_gate` (E2)

## 4. Do-not-borrow

- Dual-phase NREM/REM or CLS dual-sleep as required architecture
- Active Inference as formal proof of allostasis
- Pure internal homeostatic reward without owner/hard outcomes
- Agent-readable self-optimizable quality composites
- Fact-blocking framed as “immunity”
- Unbounded cortisol/anxiety drive
- DGM self-edit of core / safety spine
- Empty idle greetings; 31k prompt dumps; auto personality rewrite

## 5. Execution order

| Step | Work | Status |
|------|------|--------|
| E0 | Freeze constraints in this plan | done |
| E1 | H4 agent-blind + hard outcomes + offline reweight API | **done 2026-07-17** (`xinyu_nine_score`, tests) |
| E2 | Influence-governed memory gate min slice | **done 2026-07-17** (`xinyu_memory_influence_gate` + living recall hook) |
| E3 | PE / predicted deviation / satiety on proactive | **done 2026-07-17** (`xinyu_allostatic_initiative` + motivation) |
| E4 | Joint priority queue device+maintenance+proactive | **done 2026-07-17** (`xinyu_tick_priority_queue` + scout hook) |
| E5 | Method/source immunity on write/skill | **done 2026-07-17** (`xinyu_method_immunity` + write_skill + write_policy) |
| E6 | RPE skill promote | **done light** (`record_skill_outcome`) |
| E7 | hard-outcome A/B equal vs reweight | **done 2026-07-17** (`xinyu_nine_score_ab` + status fields) |

### Residual wiring (same day)

- Maintenance `run_autonomous_maintenance_once` consults tick queue before heavy spawn
- `load_nine_score(..., agent_safe=True)` + `refresh_nine_scorecard` + agent-safe mirror file
- Optional auto reweight via `XINYU_NINE_SCORE_AUTO_REWEIGHT=1` (env.example)
- Status: `nine_score_*` fields in `status_fields` / `xinyu_status --json`
- E7 A/B report: `runtime/quality/nine_score_ab_latest.json` + history jsonl

### Evidence (2026-07-17)

```text
# E1–E3
pytest tests/test_nine_score.py tests/test_memory_influence_gate.py \
  tests/test_allostatic_initiative.py tests/test_skill_rpe_promote.py \
  tests/test_proactive_motivation.py -q
→ 23 passed

# E4–E5 + residual + bridge maintenance regression
pytest tests/test_tick_priority_queue.py tests/test_method_immunity.py \
  tests/test_maintenance_tick_queue.py tests/test_bridge_autonomous_maintenance.py \
  tests/test_nine_score.py ... -q
→ 93 passed
```

## 6. Module map

| Module | Cards |
|--------|-------|
| `xinyu_nine_score` | 1 |
| OCS / recall / candidates | 10 |
| `xinyu_proactive_motivation` | 2,3,5 |
| `xinyu_skill_library` | 6,8 |
| autonomous maintenance / scout | 2,4,7,10 |
| `xinyu_device_resource_gate` | 7 |
| silence / future_effect | 3,4,5 + H4 hard layer |

## 7. Sources (primary)

- Chen et al. 2026 criterion validity / Goodhart: https://arxiv.org/html/2604.00022v1
- Kelkar 2021 cognitive homeostatic agents: https://arxiv.org/pdf/2103.03359
- Khan & Lowe 2024 allostasis PE: https://arxiv.org/abs/2406.08471
- Sterling 2012 allostasis: https://pubmed.ncbi.nlm.nih.gov/21684297/
- Schulkin & Sterling 2019: https://pubmed.ncbi.nlm.nih.gov/31488322/
- Piovarchy & Siskind 2023 epistemic immunity: https://link.springer.com/article/10.1007/s11098-023-01993-9
- MRMS influence governance 2026: https://arxiv.org/html/2607.04617v1

## 8. Caveats

Allostasis sources are design metaphors + min-tests, not biophysiology claims.  
Chen n=60 supports modal Goodhart/dilution risk.  
MRMS is synthetic diagnostics — adopt framing (influence governance), not full rewrite.
