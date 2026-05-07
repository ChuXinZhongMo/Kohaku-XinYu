"""Configurable tool call format for the stream parser."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolCallFormat:
    """
    Defines the delimiters and style for tool call syntax.

    Two key format families:
    - Bracket: [/tool]@@arg=val\\ncontent[tool/]  (slash_means_open=True)
    - XML:     <tool arg="val">content</tool>     (slash_means_open=False)

    The state machine uses these to detect opening/closing tags:
    - See start_char -> might be a tag
    - See slash after start_char:
      - slash_means_open=True  -> it's an OPENING tag (bracket: [/name])
      - slash_means_open=False -> it's a CLOSING tag (XML: </name>)
    - See letter after start_char:
      - slash_means_open=True  -> it's a CLOSING tag (bracket: [name/])
      - slash_means_open=False -> it's an OPENING tag (XML: <name>)
    """

    start_char: str = "["
    end_char: str = "]"
    slash_means_open: bool = True
    arg_style: str = "line"  # "line" = @@key=val per line, "inline" = key="val" in tag
    arg_prefix: str = "@@"
    arg_kv_sep: str = "="


# Presets
BRACKET_FORMAT = ToolCallFormat()
XML_FORMAT = ToolCallFormat(
    start_char="<",
    end_char=">",
    slash_means_open=False,
    arg_style="inline",
    arg_prefix="",
)


def format_tool_call_example(
    fmt: ToolCallFormat,
    name: str,
    args: dict[str, str] | None = None,
    body: str = "",
) -> str:
    """Generate a tool call example string from a ToolCallFormat.

    Used by prompt generators to show format-correct examples
    regardless of the configured format (bracket, xml, custom).
    """
    s, e = fmt.start_char, fmt.end_char

    # Opening tag
    if fmt.slash_means_open:
        # Bracket style: [/name]
        open_tag = f"{s}/{name}{e}"
        close_tag = f"{s}{name}/{e}"
    else:
        # XML style: <name> or <name arg="val">
        open_tag = f"{s}{name}{e}"
        close_tag = f"{s}/{name}{e}"

    # Inline args (XML style): <name key="val" key2="val2">
    if args and fmt.arg_style == "inline":
        attr_str = " ".join(f'{k}="{v}"' for k, v in args.items())
        if fmt.slash_means_open:
            open_tag = f"{s}/{name} {attr_str}{e}"
        else:
            open_tag = f"{s}{name} {attr_str}{e}"

    parts = [open_tag]

    # Line-style args: @@key=value per line
    if args and fmt.arg_style == "line":
        for k, v in args.items():
            parts.append(f"{fmt.arg_prefix}{k}{fmt.arg_kv_sep}{v}")

    if body:
        parts.append(body)

    parts.append(close_tag)
    return "\n".join(parts)
