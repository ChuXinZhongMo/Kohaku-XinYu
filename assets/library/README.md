# XinYu Library

External reference material lives here.

This directory is not lived memory. Material here may inform research notes,
retrieval candidates, or reviewed learning summaries, but it must not directly
rewrite owner-private memory, relationship state, persona state, or emotional
state.

## Buckets

- `papers/`: extracted papers and academic notes.
- `datasets/`: public or reviewed external datasets. Compatibility loaders
  resolve `assets/library/datasets/` before falling back to the older
  `library/datasets/` path and the legacy app-local `data/external/`.
  Dataset CLI tools may now resolve `--dataset-id` / `--dataset-name` directly
  from this bucket when no explicit `--dataset` path is supplied.
- `notes/`: short source-backed implementation notes.
