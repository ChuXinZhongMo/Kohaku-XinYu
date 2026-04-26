"""Assistant message block — accumulates streaming text in the live region."""

from rich.console import Console, ConsoleOptions, Group, RenderableType, RenderResult
from rich.markdown import Markdown
from rich.segment import Segment
from rich.style import Style
from rich.text import Text

from kohakuterrarium.builtins.cli_rich.theme import COLOR_AI, ICON_AI

# Markers that indicate the buffer has markdown-worthy structure.
_MARKDOWN_HINTS = ("```", "**", "__", "##", "- ", "* ", "1. ", "> ", "[", "`")


def _looks_like_markdown(text: str) -> bool:
    return any(hint in text for hint in _MARKDOWN_HINTS)


class PrefixedRenderable:
    """Render an inner renderable with an icon prefixing the first line.

    Used to keep the assistant message format consistent: ``◆ first line``
    inline, with subsequent lines indented to align under the text. Without
    this, ``Group(header, body)`` puts the icon on its own line and the
    body starts on the next line — which is what the user complained about.
    """

    def __init__(
        self,
        icon: str,
        icon_style: str,
        body: RenderableType,
        indent_width: int = 2,
    ):
        self.icon = icon
        self.icon_style = icon_style
        self.body = body
        self.indent_width = indent_width

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        sub_options = options.update_width(
            max(1, options.max_width - self.indent_width)
        )
        lines = list(console.render_lines(self.body, sub_options, pad=False))
        icon_seg = Segment(self.icon, Style.parse(self.icon_style))
        indent_seg = Segment(" " * self.indent_width)
        for i, line in enumerate(lines):
            yield icon_seg if i == 0 else indent_seg
            yield from line
            yield Segment.line()


class AssistantMessageBlock:
    """Streaming text accumulator for the live region.

    During streaming, ``__rich__`` returns a Text with all accumulated
    chunks (cheap, no markdown re-parse on every chunk). When the message
    is complete, ``to_committed()`` returns rich.markdown.Markdown if the
    buffer looks markdown-worthy.
    """

    def __init__(self):
        self._buffer: str = ""
        self._finished: bool = False

    def append(self, chunk: str) -> None:
        if not chunk:
            return
        self._buffer += chunk

    def finish(self) -> None:
        self._finished = True

    @property
    def text(self) -> str:
        return self._buffer

    @property
    def is_empty(self) -> bool:
        return not self._buffer.strip()

    def __rich__(self) -> RenderableType:
        if self.is_empty:
            return Text("")
        header = Text(f"{ICON_AI} ", style=COLOR_AI)
        body = Text(self._buffer)
        return Group(Text.assemble(header, body))

    def to_committed(self) -> RenderableType:
        """Return the renderable to print to scrollback when message is done.

        Uses Rich Markdown if the buffer contains markdown markers,
        otherwise falls back to plain text. Either way the icon (◆) is
        rendered ON THE SAME LINE as the first line of the body via
        PrefixedRenderable, so the layout matches the live streaming form.
        """
        if self.is_empty:
            return Text("")
        if _looks_like_markdown(self._buffer):
            body: RenderableType = Markdown(self._buffer, code_theme="monokai")
        else:
            body = Text(self._buffer)
        return PrefixedRenderable(f"{ICON_AI} ", COLOR_AI, body)
