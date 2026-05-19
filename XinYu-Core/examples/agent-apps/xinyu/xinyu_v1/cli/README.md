# XinYu v1 CLI Policy

The v1 CLI folder contains operator and shadow-runtime commands. These files
are intentionally import-light and are not part of the live turn path unless an
operator runs them explicitly.

## Registered Commands

- `inspect_memory.py`: inspect v1 memory retrieval output for a query.
- `migrate_memory.py`: dry-run or apply legacy Markdown memory migration into
  the v1 vector-store abstraction.
- `run_maintenance.py`: run v1 maintenance from the CLI.
- `smoke.py`: run v1 CLI smoke checks.

## Keep/Retire Rule

- Keep `inspect_memory.py` while v1 memory shadow inspection is available.
- Keep `migrate_memory.py` while legacy Markdown migration is still a supported
  recovery path.
- If v1 memory is retired or replaced by the canonical live recall path only,
  archive these commands in the same batch and update this README.
- Do not route live chat through these commands.
