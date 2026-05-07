"""Runtime filesystem paths for XinYu."""

from pathlib import Path

XINYU_HOME = Path.home() / ".xinyu"


def xinyu_path(*parts: str) -> Path:
    """Return a path under XinYu's primary runtime home."""
    return XINYU_HOME.joinpath(*parts)


def readable_path(*parts: str) -> Path:
    """Return the XinYu path used for reads."""
    return xinyu_path(*parts)


def readable_dirs(*parts: str) -> list[Path]:
    """Return the XinYu directory if it exists."""
    directory = xinyu_path(*parts)
    return [directory] if directory.exists() else []
