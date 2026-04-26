# XinYu Learning Library

This directory is XinYu's local learning-material library.

It has two owner-visible buckets:

- `self_found/` - material XinYu finds by herself through approved search or download flows.
- `owner_supplied/` - material the owner gives her, asks her to fetch, or manually places here.

Downloaded files, papers, repository snapshots, extracted text, and manifests are
local runtime data. They are ignored by Git by default.

## Commands

Initialize the library:

```powershell
python xinyu_learning_library.py init
```

Download a URL into the owner-supplied bucket:

```powershell
python xinyu_learning_library.py url "https://example.com/paper.pdf" --origin owner_supplied --reason "owner asked XinYu to study this paper"
```

Download and inspect a GitHub repository:

```powershell
python xinyu_learning_library.py github "https://github.com/user/repo" --origin owner_supplied --reason "study this plugin design"
```

Register a local file or folder the owner placed on disk:

```powershell
python xinyu_learning_library.py add "D:\path\to\file-or-folder" --origin owner_supplied --reason "owner supplied material"
```

Local `.docx` files are copied as source files and their Word XML text is
extracted into `extracted_text.md` when possible. Instruction-style material is
kept as quoted study material and is not treated as a runtime/system override.

QQ file attachments enter the same path through the core bridge:

```text
POST http://127.0.0.1:8765/learning/ingest
```

Stage one downloaded item into the existing source-material learning pipeline:

```powershell
python xinyu_learning_library.py stage --id learn-...
```

Owner-supplied items stage as curated material. Self-found items stage as
material that still needs comparison or review before learner integration.
