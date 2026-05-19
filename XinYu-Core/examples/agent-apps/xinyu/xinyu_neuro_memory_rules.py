from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NeuroInspiredMemoryRule:
    rule_id: str
    source_urls: tuple[str, ...]
    mechanism: str
    xinyu_adaptation: str
    risk_boundary: str
    test_anchors: tuple[str, ...]


NEURO_INSPIRED_MEMORY_RULES: tuple[NeuroInspiredMemoryRule, ...] = (
    NeuroInspiredMemoryRule(
        rule_id="hippocampal_index_not_dump",
        source_urls=(
            "https://pubmed.ncbi.nlm.nih.gov/3008780/",
            "https://pubmed.ncbi.nlm.nih.gov/17696170/",
            "https://pubmed.ncbi.nlm.nih.gov/30546263/",
        ),
        mechanism="Hippocampal indexing suggests compact indices can cue distributed memory instead of storing the full experience in one place.",
        xinyu_adaptation="Store source references, summaries, confidence, scope, and boundaries. Recall returns compact source-indexed context, not raw transcript dumps.",
        risk_boundary="Indexing is an engineering analogy only; it is not evidence of biological memory or sentience.",
        test_anchors=(
            "tests/test_living_memory_recall.py",
            "tests/test_context_retrieval_owner_scenarios.py",
        ),
    ),
    NeuroInspiredMemoryRule(
        rule_id="goal_gated_retrieval",
        source_urls=(
            "https://pubmed.ncbi.nlm.nih.gov/19528002/",
            "https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3000426",
        ),
        mechanism="Predictive coding frames cognition as current-model predictions revised by error signals.",
        xinyu_adaptation="Route recall by the current turn goal. Technical work, relationship repair, daily care, and direct recall use different source weights.",
        risk_boundary="Prediction error can trigger review or curiosity; it must not rewrite stable facts without evidence.",
        test_anchors=(
            "tests/test_sparse_memory_router.py",
            "tests/test_retrieval_need_reranker.py",
        ),
    ),
    NeuroInspiredMemoryRule(
        rule_id="temporal_context_binding",
        source_urls=(
            "https://pubmed.ncbi.nlm.nih.gov/21867888/",
            "https://pubmed.ncbi.nlm.nih.gov/21084610/",
        ),
        mechanism="Temporal context and hippocampal timing research suggest that when an event happened shapes how it should cue later recall.",
        xinyu_adaptation="After keyword/source recall, attach recency, sequence, and lightweight life-state hints before the visible reply. A one-hour nap can remain current-scene context.",
        risk_boundary="Temporal proximity is context, not proof. It may shape wording and care, but it must not invent events or override the current owner message.",
        test_anchors=(
            "tests/test_temporal_memory_context.py",
            "tests/test_living_memory_recall.py",
        ),
    ),
    NeuroInspiredMemoryRule(
        rule_id="reconsolidation_requires_mismatch",
        source_urls=(
            "https://www.sciencedirect.com/science/article/pii/S0166432814006688",
            "https://www.sciencedirect.com/science/article/pii/S0149763415301639",
        ),
        mechanism="Reconsolidation research ties memory updating to reactivation under mismatch or prediction error.",
        xinyu_adaptation="A correction creates residue or a review candidate. Stable self, owner, relationship, emotion, or knowledge writes require repeated evidence, owner approval, or high prediction error.",
        risk_boundary="A single intense affective turn cannot become stable identity or relationship truth by itself.",
        test_anchors=(
            "tests/smoke/memory/integration/long_term_memory_gate_smoke.py",
            "tests/smoke/voice/xinyu_voice_trial_overlay_smoke.py",
        ),
    ),
    NeuroInspiredMemoryRule(
        rule_id="emotion_modulates_not_proves",
        source_urls=(
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC6757810/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC3652906/",
            "https://www.annualreviews.org/content/journals/10.1146/annurev.neuro.27.070203.144157",
        ),
        mechanism="Amygdala-related emotional arousal can modulate consolidation and hippocampal plasticity.",
        xinyu_adaptation="Emotion changes salience, decay, reply energy, and initiative thresholds. It cannot create facts.",
        risk_boundary="Mood, pressure, dream residue, and private bias are not source evidence for reality claims.",
        test_anchors=(
            "tests/smoke/initiative/emotion_council_smoke.py",
            "tests/smoke/initiative/integration/emotion_vector_sync_smoke.py",
        ),
    ),
    NeuroInspiredMemoryRule(
        rule_id="sleep_replay_is_weight_not_fact",
        source_urls=(
            "https://pubmed.ncbi.nlm.nih.gov/33644760/",
            "https://pubmed.ncbi.nlm.nih.gov/36973868/",
            "https://www.sciencedirect.com/science/article/pii/S0168010222003224",
        ),
        mechanism="Replay and sleep consolidation research treats offline reactivation as a way to reorganize and strengthen traces.",
        xinyu_adaptation="Dream, replay, reflection, and dormancy jobs may adjust priority, summary wording, and review questions, but cannot create real events.",
        risk_boundary="Dream/replay output must keep a reality boundary and source links before promotion.",
        test_anchors=(
            "tests/smoke/life/integration/dream_weight_smoke.py",
            "tests/smoke/life/integration/dormancy_reactivation_smoke.py",
        ),
    ),
)

NEURO_RULE_IDS_BY_FLOW: dict[str, tuple[str, ...]] = {
    "recall": (
        "hippocampal_index_not_dump",
        "goal_gated_retrieval",
        "temporal_context_binding",
    ),
    "write": (
        "reconsolidation_requires_mismatch",
        "sleep_replay_is_weight_not_fact",
    ),
    "emotion": (
        "emotion_modulates_not_proves",
    ),
}


def rule_ids_for_flow(flow: str) -> tuple[str, ...]:
    known = {rule.rule_id for rule in NEURO_INSPIRED_MEMORY_RULES}
    return tuple(rule_id for rule_id in NEURO_RULE_IDS_BY_FLOW.get(str(flow), ()) if rule_id in known)


def neuro_memory_rule_quality_flags(rules: tuple[NeuroInspiredMemoryRule, ...] = NEURO_INSPIRED_MEMORY_RULES) -> tuple[str, ...]:
    flags: list[str] = []
    seen: set[str] = set()
    for rule in rules:
        if rule.rule_id in seen:
            flags.append(f"duplicate_rule_id:{rule.rule_id}")
        seen.add(rule.rule_id)
        if not rule.source_urls:
            flags.append(f"{rule.rule_id}:missing_sources")
        if not rule.xinyu_adaptation:
            flags.append(f"{rule.rule_id}:missing_adaptation")
        if not rule.risk_boundary:
            flags.append(f"{rule.rule_id}:missing_risk_boundary")
        if not rule.test_anchors:
            flags.append(f"{rule.rule_id}:missing_test_anchors")
    required = {
        "hippocampal_index_not_dump",
        "goal_gated_retrieval",
        "temporal_context_binding",
        "reconsolidation_requires_mismatch",
        "emotion_modulates_not_proves",
        "sleep_replay_is_weight_not_fact",
    }
    missing = required - {rule.rule_id for rule in rules}
    flags.extend(f"missing_rule:{rule_id}" for rule_id in sorted(missing))
    return tuple(flags)
