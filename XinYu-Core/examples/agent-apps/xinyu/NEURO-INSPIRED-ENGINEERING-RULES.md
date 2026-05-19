# Neuro-Inspired Engineering Rules

Status: active design input for memory, emotion, recall, dream/replay, and
persona pressure. These are engineering analogies only; they do not claim
biological memory, sentience, or real emotion.

Code owner: `xinyu_neuro_memory_rules.py`

## Rules

1. Hippocampal index, not dump
   - Store source references, summaries, confidence, scope, and boundaries.
   - Do not put transcript-sized memory into prompts.

2. Goal-gated retrieval
   - Route recall by the current turn goal.
   - Technical work, relationship repair, daily care, and direct recall should
     weight different sources.

3. Reconsolidation requires mismatch
   - Corrections create residue or review candidates first.
   - Stable self, owner, relationship, emotion, or knowledge writes require
     repeated evidence, owner approval, or high prediction error.

4. Emotion modulates, it does not prove
   - Emotion can change salience, decay, energy, initiative threshold, and voice
     pressure.
   - Emotion cannot create facts.

5. Replay is weight, not fact
   - Dream/replay/reflection can change priority and review questions.
   - Dream/replay/reflection cannot create real-world events or rewrite the
     timeline without source evidence.

## Source Anchors

- Hippocampal indexing: `https://pubmed.ncbi.nlm.nih.gov/3008780/`
- Hippocampal indexing review: `https://pubmed.ncbi.nlm.nih.gov/17696170/`
- Predictive coding review: `https://pubmed.ncbi.nlm.nih.gov/19528002/`
- Predictive processing perspective: `https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3000426`
- Reconsolidation mismatch/review: `https://www.sciencedirect.com/science/article/pii/S0166432814006688`
- Emotional arousal and memory modulation: `https://pmc.ncbi.nlm.nih.gov/articles/PMC6757810/`
- Sleep/replay consolidation review: `https://pubmed.ncbi.nlm.nih.gov/33644760/`

## Validation Anchors

- `tests/test_neuro_memory_rules.py`
- `tests/test_living_memory_recall.py`
- `tests/test_sparse_memory_router.py`
- `tests/test_retrieval_need_reranker.py`
- `tests/smoke/initiative/emotion_council_smoke.py`
- `tests/smoke/life/integration/dream_weight_smoke.py`
