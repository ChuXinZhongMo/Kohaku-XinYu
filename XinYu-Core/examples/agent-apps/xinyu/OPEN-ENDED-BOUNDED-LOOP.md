# Open-Ended Bounded Loop

This note defines the bounded version of XinYu's open-ended action loop.

```text
action
-> outcome
-> experience
-> audit
-> reviewable follow-up candidate
-> owner/gate decision
```

Open-ended means XinYu can accumulate evidence from bounded real actions and may later surface a small reviewable follow-up candidate. It does not mean autonomous exploration, broader disk access, self-directed permission growth, or identity rewrites.

Bounded means every executable step still depends on the existing gates:

- owner or gate approval when required
- narrow tool whitelist
- registered target aliases
- read/write scope boundaries
- factual `ActionOutcome` before expressive reply
- `ExperienceFrame` before metabolism or memory candidates

The audit step is intentionally read-only. `xinyu_action_openended_audit.py` only answers whether current action experience sedimentation is healthy: whether low-salience action material leaked into residue/dream/reflection, whether action themes are over-repeating, and whether visible phrase motifs are being amplified.

The audit step must not:

- generate next safe challenge candidates
- execute any action
- write memory or runtime state
- expand allowed filesystem scope
- make dream/reflection more active
- turn ordinary tool actions into stable identity or relationship memory

Follow-up candidates belong to a later proposal layer. That layer, when implemented, must produce reviewable candidates only; it must not auto-run them, enlarge permissions, or treat owner silence as failure.
