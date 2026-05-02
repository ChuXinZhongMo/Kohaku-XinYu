# XinYu Memory Seeds

This directory stores portable seed memory that should survive new worktrees and future clones.

Rules:

- Keep only portable concept/policy seed material here.
- Do not store live QQ residue, emotion logs, relationship logs, runtime traces, local secrets, raw account identifiers, or private chat exports.
- Runtime memory still lives under `memory/` and remains ignored by Git.
- Use `sync_memory_seeds.py --apply` only when a workspace needs the seed copied into local runtime memory.

Current seed files:

- `context/persona_life_anchors.md` -> `memory/context/persona_life_anchors.md`
- `context/real_world_anchor_policy.md` -> `memory/context/real_world_anchor_policy.md`
- `context/life_month_slots.md` -> `memory/context/life_month_slots.md`
- `context/codex_delegation_policy.md` -> `memory/context/codex_delegation_policy.md`
- `self/system_prompt_memory.md` -> `memory/self/system_prompt_memory.md`
