def _fmt_tokens(n: int) -> str:
    """Format token count as human-readable string."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def _summarize_output(output: str) -> str:
    if not output:
        return ""
    lines = output.strip().split("\n")
    if len(lines) <= 1 and len(output) <= 60:
        return output.strip()
    return f"{len(lines)} lines"
