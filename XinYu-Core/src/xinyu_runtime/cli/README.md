# cli/

`xinyu-runtime` command dispatcher. `xyr` is the short alias. The old `kt`
command remains as a compatibility entry point.

## Files

| File | Subcommand(s) |
| --- | --- |
| `__init__.py` | `main()` argparse setup and dispatch table |
| `run.py` | `xinyu-runtime run` |
| `resume.py` | `xinyu-runtime resume` |
| `auth.py` | `xinyu-runtime login` |
| `packages.py` | `list`, `info`, `install`, `uninstall`, `update`, `edit` |
| `model.py` | `xinyu-runtime model list/default/show` |
| `memory.py` | `xinyu-runtime embedding` and `xinyu-runtime search` |
| `serve.py` | `xinyu-runtime serve start/stop/status/logs` |
| `config.py` | `xinyu-runtime config` |
| `extension.py` | `xinyu-runtime extension list/info` |
| `mcp.py` | `xinyu-runtime mcp list` |
| `version.py` | `xinyu-runtime --version` |

The console scripts in `pyproject.toml` all invoke `cli/__init__.py:main()`.

## Notes

- `serve` writes daemon state under `~/.xinyu/run`.
- `__run-server` is a hidden internal subcommand used by `serve start`.
- `@package/path` syntax is resolved through `packages.resolve_package_path`.
