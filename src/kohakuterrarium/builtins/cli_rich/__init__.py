"""Rich CLI mode — inline three-layer model (scrollback / live region / composer).

Uses prompt_toolkit for input and Rich Live for the streaming live region,
bridged via prompt_toolkit's patch_stdout(). The result feels like Claude
Code CLI but is built entirely on existing Python libraries.

Public API:
    RichCLIApp     — orchestrator
    RichCLIInput   — InputModule subclass
    RichCLIOutput  — OutputModule subclass
"""

from kohakuterrarium.builtins.cli_rich.app import RichCLIApp
from kohakuterrarium.builtins.cli_rich.input import RichCLIInput
from kohakuterrarium.builtins.cli_rich.output import RichCLIOutput

__all__ = ["RichCLIApp", "RichCLIInput", "RichCLIOutput"]
