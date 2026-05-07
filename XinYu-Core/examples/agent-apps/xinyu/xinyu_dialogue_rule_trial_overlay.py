from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from xinyu_dialogue_rule_eval import (
    OWNER_SCOPE,
    default_cards_path,
    evaluate_text,
    parse_owner_rule_cards,
)


OVERLAY_REL = Path("runtime/life_kernel/dialogue_rule_trial_overlay.json")
DEFAULT_APPLICATIONS = 8
DEFAULT_TTL_MINUTES = 360
DEFAULT_MAX_RULES_PER_TURN = 3


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _trim(text: Any, limit: int = 220) -> str:
    clean = re.sub(r"\s+", " ", _safe_str(text)).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def _now() -> datetime:
    return datetime.now().astimezone()


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    lowered = _safe_str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _owner_private(payload: dict[str, Any] | None) -> bool:
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    is_owner = _as_bool(payload.get("is_owner_user") or metadata.get("is_owner_user"), default=False)
    group_id = _safe_str(payload.get("group_id")).strip()
    message_type = _safe_str(payload.get("message_type")).strip().lower()
    return is_owner and not group_id and not message_type.startswith("group")


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _parse_time(value: Any) -> datetime | None:
    raw = _safe_str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def _expired(state: dict[str, Any], now_dt: datetime) -> bool:
    if _safe_str(state.get("status")) != "active":
        return True
    try:
        remaining = int(state.get("remaining_applications") or 0)
    except (TypeError, ValueError):
        remaining = 0
    if remaining <= 0:
        return True
    expires_at = _parse_time(state.get("expires_at"))
    return bool(expires_at and now_dt >= expires_at)


def _trial_id(activated_at: str, rule_count: int) -> str:
    total = sum((idx + 1) * ord(ch) for idx, ch in enumerate(f"{activated_at}:{rule_count}"))
    return f"dialogue-rule-trial-{total % 1_000_000:06d}"


def activate_dialogue_rule_trial_overlay(
    root: Path,
    *,
    activated_at: str | None = None,
    applications: int = DEFAULT_APPLICATIONS,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
    max_rules_per_turn: int = DEFAULT_MAX_RULES_PER_TURN,
    source: str = "owner_approved_dialogue_rule_cards",
) -> dict[str, Any]:
    cards_path = default_cards_path(root)
    cards = parse_owner_rule_cards(cards_path)
    now_dt = _now()
    activated_at = activated_at or now_dt.isoformat(timespec="seconds")
    applications = max(1, min(24, int(applications)))
    max_rules_per_turn = max(1, min(5, int(max_rules_per_turn)))
    state = {
        "version": 1,
        "status": "active",
        "trial_id": _trial_id(activated_at, len(cards)),
        "source": source,
        "cards_path": str(cards_path),
        "approved_rule_count": len(cards),
        "activated_at": activated_at,
        "updated_at": activated_at,
        "remaining_applications": applications,
        "initial_applications": applications,
        "max_rules_per_turn": max_rules_per_turn,
        "expires_at": (now_dt + timedelta(minutes=max(1, int(ttl_minutes)))).isoformat(timespec="seconds"),
        "stable_profile_write": "blocked",
        "stable_relationship_write": "blocked",
        "runtime_integration_scope": "owner_private_short_term_prompt_sidecar",
        "model_training": "blocked",
        "promotion_gate": "required_for_stable_voice_or_profile_change",
        "notes": [
            "dialogue_rule_trial_overlay_runtime_only",
            "owner_private_only",
            "applies_only_when_current_text_matches_approved_rule",
        ],
    }
    _write_state(root / OVERLAY_REL, state)
    return {
        "activated": True,
        "path": str(root / OVERLAY_REL),
        "trial_id": state["trial_id"],
        "approved_rule_count": len(cards),
        "remaining_applications": applications,
        "boundary": (
            "short-term owner-private prompt sidecar only; stable_profile_write blocked; "
            "runtime integration limited to this overlay; model_training blocked"
        ),
    }


def read_dialogue_rule_trial_overlay(root: Path) -> dict[str, Any]:
    return _read_state(root / OVERLAY_REL)


def build_dialogue_rule_trial_overlay_prompt_block(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    consume_application: bool = True,
    now_dt: datetime | None = None,
) -> str:
    if not _owner_private(payload):
        return ""
    now_dt = now_dt or _now()
    path = root / OVERLAY_REL
    state = _read_state(path)
    if not state:
        return ""
    if _expired(state, now_dt):
        if _safe_str(state.get("status")) == "active":
            state["status"] = "expired"
            state["updated_at"] = now_dt.isoformat(timespec="seconds")
            _write_state(path, state)
        return ""

    cards_path = Path(_safe_str(state.get("cards_path"))) if _safe_str(state.get("cards_path")) else default_cards_path(root)
    try:
        cards = parse_owner_rule_cards(cards_path)
        matches = evaluate_text(cards, user_text, source_kind=OWNER_SCOPE)
    except Exception:
        return ""
    if not matches:
        return ""

    try:
        max_rules_per_turn = int(state.get("max_rules_per_turn") or DEFAULT_MAX_RULES_PER_TURN)
    except (TypeError, ValueError):
        max_rules_per_turn = DEFAULT_MAX_RULES_PER_TURN
    selected = matches[: max(1, min(5, max_rules_per_turn))]

    try:
        remaining_before = int(state.get("remaining_applications") or 0)
    except (TypeError, ValueError):
        remaining_before = 0
    remaining_after = max(0, remaining_before - 1) if consume_application else remaining_before
    if consume_application:
        state["remaining_applications"] = remaining_after
        state["updated_at"] = now_dt.isoformat(timespec="seconds")
        state["last_applied_at"] = now_dt.isoformat(timespec="seconds")
        state["last_owner_text"] = _trim(user_text, limit=180)
        state["last_matched_rules"] = [match.rule_key for match in selected]
        if remaining_after <= 0:
            state["status"] = "expired_applications_consumed"
        _write_state(path, state)

    rule_by_key = {card.rule_key: card for card in cards}
    lines = [
        "dialogue rule trial overlay sidecar:",
        "- scope: owner_private_short_term",
        f"- trial_id: {_safe_str(state.get('trial_id'), 'unknown')}",
        f"- remaining_applications_after_this_turn: {remaining_after}",
        f"- expires_at: {_safe_str(state.get('expires_at'), 'unknown')}",
        "- matched_rule_count: " + str(len(selected)),
    ]
    for idx, match in enumerate(selected, start=1):
        card = rule_by_key.get(match.rule_key)
        fields = card.fields if card else {}
        lines.extend(
            [
                f"- rule_{idx}: {match.rule_key}",
                f"  trigger: {_trim(fields.get('trigger'), limit=180)}",
                f"  behavior_bias: {_trim(fields.get('xinyu_rule'), limit=220)}",
                f"  avoid: {_trim(fields.get('xinyu_do_not_learn'), limit=180)}",
            ]
        )
    lines.extend(
        [
            "- boundary: short-term runtime overlay only; convert the rule into the next natural line.",
            "- do_not_say: do not mention rules, trial overlays, cards, files, scores, gates, or matching.",
            "- stable_profile_write: blocked; stable_relationship_write: blocked; model_training: blocked.",
        ]
    )
    return "\n".join(lines)


def clear_dialogue_rule_trial_overlay(root: Path) -> bool:
    path = root / OVERLAY_REL
    if not path.exists():
        return False
    state = _read_state(path)
    state["status"] = "cleared"
    state["remaining_applications"] = 0
    state["updated_at"] = _now().isoformat(timespec="seconds")
    _write_state(path, state)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Activate or inspect XinYu's short-term dialogue-rule trial overlay.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--applications", type=int, default=DEFAULT_APPLICATIONS)
    parser.add_argument("--ttl-minutes", type=int, default=DEFAULT_TTL_MINUTES)
    parser.add_argument("--max-rules-per-turn", type=int, default=DEFAULT_MAX_RULES_PER_TURN)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if args.clear:
        print(json.dumps({"cleared": clear_dialogue_rule_trial_overlay(root)}, ensure_ascii=False, indent=2))
        return 0
    if args.activate:
        result = activate_dialogue_rule_trial_overlay(
            root,
            applications=args.applications,
            ttl_minutes=args.ttl_minutes,
            max_rules_per_turn=args.max_rules_per_turn,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(json.dumps(read_dialogue_rule_trial_overlay(root), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
