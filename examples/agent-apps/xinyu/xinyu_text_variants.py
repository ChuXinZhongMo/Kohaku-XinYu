from __future__ import annotations


LEGACY_MOJIBAKE_ENCODINGS = ("gbk", "gb18030", "cp936")


def legacy_mojibake_variants(text: str) -> tuple[str, ...]:
    """Return legacy mojibake forms without storing unreadable markers in source."""
    variants: list[str] = []
    seen: set[str] = {text}
    raw = text.encode("utf-8")
    for encoding in LEGACY_MOJIBAKE_ENCODINGS:
        for errors in ("strict", "replace", "ignore"):
            try:
                variant = raw.decode(encoding, errors=errors)
            except UnicodeDecodeError:
                continue
            for candidate in (variant, variant.replace("\ufffd", "?")):
                if candidate and candidate not in seen:
                    seen.add(candidate)
                    variants.append(candidate)
    return tuple(variants)


def readable_markers(*markers: str) -> tuple[str, ...]:
    """Keep marker lists readable while still matching old corrupted input/logs."""
    expanded: list[str] = []
    seen: set[str] = set()
    for marker in markers:
        for candidate in (marker, *legacy_mojibake_variants(marker)):
            if candidate and candidate not in seen:
                seen.add(candidate)
                expanded.append(candidate)
    return tuple(expanded)
