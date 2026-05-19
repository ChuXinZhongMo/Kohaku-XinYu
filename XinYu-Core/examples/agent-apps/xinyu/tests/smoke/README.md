# Smoke Scripts

This directory holds executable smoke scripts that are useful during local maintenance but are not normal pytest modules.

Conventions:

- Keep direct execution working with `python tests/smoke/<area>/<script>.py`.
- Add a local bootstrap when a moved script imports root-level XinYu modules.
- Prefer moving pure helper checks here before moving live-service or integration smokes.
- Put live-service or heavier local integration checks under an `integration/` subdirectory.
- Leave runtime, private state, and generated snapshots out of this tree.
