from __future__ import annotations

import re
import unicodedata

from xinyu_text_variants import looks_like_legacy_mojibake


def claim_looks_garbled(claim: str) -> bool:
    sample = claim.strip()[:2000]
    if looks_like_legacy_mojibake(sample):
        return True
    mojibake_markers = sum(
        sample.count(marker)
        for marker in ("\u951f\u65a4\u62f7", "\u951f\u65a4", "\u65a4\u62f7", "\ufffd\ufffd", "\ufffd\ufffd\ufffd")
    )
    chars = [char for char in sample if not char.isspace()]
    if len(chars) < 24:
        return False
    control_or_replacement = sum(
        1
        for char in chars
        if char == "\ufffd" or unicodedata.category(char) in {"Cc", "Cf", "Cs"}
    )
    private_use = sum(1 for char in chars if 0xE000 <= ord(char) <= 0xF8FF or unicodedata.category(char) == "Co")
    rare_cjk = sum(
        1
        for char in chars
        if 0x3400 <= ord(char) <= 0x4DBF or 0x20000 <= ord(char) <= 0x2FA1F
    )
    uncommon_latin = sum(1 for char in chars if 0x1D00 <= ord(char) <= 0x1EFF or 0xA720 <= ord(char) <= 0xABFF)
    total = len(chars)
    if mojibake_markers >= 2 and (mojibake_markers * 3) / total > 0.01:
        return True
    if control_or_replacement and control_or_replacement / total > 0.004:
        return True
    if private_use and private_use / total > 0.003:
        return True
    if total >= 80 and (rare_cjk + uncommon_latin + private_use + control_or_replacement) / total > 0.18:
        return True
    return False


def claim_is_placeholder(claim: str) -> bool:
    normalized = re.sub(r"\s+", " ", claim.strip().lower())
    return normalized.startswith("owner/local material copied from ") or normalized.startswith("downloaded ")


def claim_is_too_thin(claim: str) -> bool:
    tokens = [token for token in re.findall(r"[a-z0-9]+", claim.lower()) if len(token) > 2]
    cjk_chars = [char for char in claim if "\u4e00" <= char <= "\u9fff"]
    return len(tokens) < 8 and len(cjk_chars) < 24
