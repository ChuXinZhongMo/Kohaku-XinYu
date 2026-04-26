from typing import ClassVar

from textual.events import Key
from textual.message import Message
from textual.widgets import TextArea

# ── Chat Input ─────────────────────────────────────────────────


class ChatInput(TextArea):
    """Multi-line input. Enter sends, Shift+Enter or Ctrl+J inserts newline.

    Ctrl+J works universally (including SSH) since it is the literal
    newline character and does not depend on terminal modifier support.
    """

    DEFAULT_CSS = """
    ChatInput {
        height: auto;
        min-height: 3;
        max-height: 8;
        border: solid #5A4FCF 30%;
    }
    ChatInput:focus {
        border: solid #5A4FCF;
    }
    """

    # Available commands — set by TUI app for hint display
    command_names: ClassVar[list[str]] = []

    class Submitted(Message):
        """Posted when the user presses Enter to send."""

        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    class EditQueued(Message):
        """Posted when user presses Up on empty input to edit last queued message."""

        pass

    class CommandHint(Message):
        """Posted when user is typing a / command, for hint display."""

        def __init__(self, hint: str) -> None:
            super().__init__()
            self.hint = hint

    def on_text_area_changed(self) -> None:
        """Show command hints when typing /."""
        text = self.text.strip()
        if text.startswith("/") and self.command_names:
            partial = text.lstrip("/").split()[0].lower() if text.strip("/") else ""
            matches = [n for n in self.command_names if n.startswith(partial)]
            if matches and partial:
                hint = "  ".join(f"/{m}" for m in matches[:6])
                self.post_message(self.CommandHint(hint))
            elif not partial:
                hint = "  ".join(f"/{n}" for n in self.command_names[:8])
                self.post_message(self.CommandHint(hint))
            else:
                self.post_message(self.CommandHint(""))
        else:
            self.post_message(self.CommandHint(""))

    def _on_key(self, event: Key) -> None:
        # Shift+Enter, Ctrl+Enter, Ctrl+J: insert newline
        if event.key in ("shift+enter", "ctrl+enter", "ctrl+j"):
            event.prevent_default()
            event.stop()
            self.insert("\n")
            return
        # Plain Enter: send message
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            text = self.text.strip()
            if text:
                self.post_message(self.Submitted(text))
                self.clear()
            return
        # Up arrow on empty input: edit last queued message
        if event.key == "up" and not self.text.strip():
            event.prevent_default()
            event.stop()
            self.post_message(self.EditQueued())
            return
        super()._on_key(event)
