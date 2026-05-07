# builtins/inputs/

Built-in input module implementations. Input modules receive external input
(terminal, speech, API) and produce `TriggerEvent` objects for the controller.
The `__init__.py` provides a registry with factory functions so that
`bootstrap/io.py` can create input modules by name. TUI and Whisper inputs
are registered at import time when their dependencies are available.

## Files

| File | Description |
|------|-------------|
| `__init__.py` | Input registry, factory functions, builtin registration |
| `cli.py` | `CLIInput` (blocking terminal) and `NonBlockingCLIInput` (non-blocking polling) |
| `none.py` | `NoneInput` for trigger-only agents with no user input |
| `asr.py` | ASR base classes (`ASRModule`, `ASRConfig`, `ASRResult`) for speech-to-text |
| `whisper.py` | `WhisperASR` using openai-whisper + sounddevice + Silero VAD (optional dependency) |

## Registered Types

`cli`, `cli_nonblocking`, `none`, `tui` (from `builtins.tui`), `whisper` (optional)

## Dependencies

- `xinyu_runtime.core.events` (TriggerEvent, create_user_input_event)
- `xinyu_runtime.modules.input.base` (BaseInputModule)
- `xinyu_runtime.builtins.tui.input` (TUIInput, registered at import)
- `xinyu_runtime.utils.logging`

