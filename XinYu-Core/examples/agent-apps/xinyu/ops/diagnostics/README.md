# Diagnostics

Operator-only checks and inspection scripts live here. They are not imported by
the live turn path.

- `check_runtime_env.py` validates local runtime dependencies and env presence without printing secret values.
- `check_sent_index.py` looks up adapter message ids in the sent reply index.
- `diagnose_runtime_injection.py` inspects resolved runtime prompt/config injection without running a live turn.
- `dialogue_curiosity_review.py` summarizes dialogue-curiosity prediction errors from runtime logs for operator review.
- `mark_smoke_test.py` runs a temporary Goldmark smoke or marks a live adapter message id when explicitly given one.
- `xinyu_live_module_diagnostics.py` reports which refactored live modules influenced the latest turn.
