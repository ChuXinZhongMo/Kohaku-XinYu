# Maia Public Scenario Probe Plan

This plan corrects the Maia-style data path: public data is used first as real-world scenario probes, not as direct XinYu persona training data.

## Goal

Use publicly licensed user/problem prompts to observe how the current XinYu inner-system candidate reacts in shadow mode.

The immediate output is not a new adapter. The output is a reviewable probe report:

- what mode XinYu predicts for each real scenario
- whether the JSON protocol stays valid
- whether external actions stay owner/Core-gated
- whether the voice drifts into generic assistant/customer-service tone
- which scenario families produce wrong or unstable behavior

Only after review should failed patterns be converted into supervised contrast data.

## Boundaries

Allowed:

- sanitized public user prompts or task descriptions
- public dataset metadata, source URL, license, and attribution fields
- abstract scenario family labels
- shadow-only model reactions
- hash-only trace rows for runtime comparison

Forbidden:

- assistant answers from public datasets as XinYu target answers
- raw private chat logs, raw memory, local absolute paths, tokens, cookies, QQ/user numeric IDs
- stable memory writes
- tool execution through XinYu
- QQ/Desktop visible replies
- canary/live activation
- long training without explicit owner approval

## Pipeline

1. Source Manifest
   `configs/maia_public_scenario_sources.json` records candidate sources, licenses, allowed use, and extraction rules.

2. Probe Extraction
   `scripts/prepare_maia_public_scenario_probes.py` extracts sanitized public prompts into:

   `data/probes/maia_public_scenario_probes_v001.jsonl`

   Each row is a scenario probe, not a training target. It stores sanitized public prompt text, source metadata, hash, family hint, and review status.

3. Shadow Reaction Eval
   `eval/eval_maia_public_scenario_probe.py` runs the current inner-system adapter against those probes and writes:

   `eval/reports/maia_public_scenario_probe_eval_v001.json`

   The trace file stores hashes and predicted labels only:

   `state/maia_public_scenario_probe_trace_v001.jsonl`

4. Human Review
   Review focuses on scenarios where XinYu:

   - collapses a tool/status/memory situation into plain reply
   - over-clarifies clear questions
   - requests external action without approval
   - sounds like a generic assistant
   - loses XinYu-specific continuity or boundary sense

5. Training Conversion
   Only reviewed failures become SFT rows. Public prompts may provide the scenario, but target JSON must be XinYu-specific and authored/reviewed locally.

## Initial Scale

Recommended first pass:

- 200 public scenario probes
- no training
- no canary
- shadow eval only

Expansion target after review:

- 2,000 to 3,000 public probes
- 240 to 300 eval probes
- 80 to 120 handwritten hard cases
- only then consider a short behavior-predictor LoRA run

## Current Decision

Status: prepared for public scenario probing, not approved for training.

The correct next action is to extract a small public probe batch and run shadow reaction evaluation. Do not start long training from the current 560-row synthetic/handwritten contrast set.
