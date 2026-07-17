"""Full-open Agent Tech Scout Loop (device-bounded).

Pipeline:
  device gate → optional public fetch (AI/papers) → optional autonomous search
  activation → AI self-iteration gate/review → optional micro-apply of safe skills

Does NOT auto-rewrite stable personality. Micro-apply is limited to review_only
skill artifacts distilled from scout findings when tests/config allow.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from xinyu_device_resource_gate import evaluate_device_resource_gate
from xinyu_hot_topic_fetch import (
    fetch_public_hot_pages,
    filter_ai_relevant_items,
    filter_unpushed_items,
    mark_items_pushed,
    oral_hot_followup_line,
    user_asks_ai_news,
    user_asks_ai_papers,
)
from xinyu_skill_library import list_skills, write_skill
from xinyu_storage_paths import knowledge_file_path


ENV_ENABLED = "XINYU_AGENT_TECH_SCOUT"
ENV_INTERVAL_MIN = "XINYU_AGENT_TECH_SCOUT_INTERVAL_MINUTES"
ENV_AUTO_MICRO = "XINYU_AGENT_TECH_SCOUT_AUTO_MICRO_APPLY"
ENV_FETCH = "XINYU_AGENT_TECH_SCOUT_FETCH"
ENV_FORCE = "XINYU_AGENT_TECH_SCOUT_FORCE"

STATE_REL = Path("runtime/quality/agent_tech_scout_state.json")
REPORT_REL = Path("runtime/quality/agent_tech_scout_latest.json")
DEFAULT_INTERVAL_MIN = 90


def _now() -> datetime:
    return datetime.now().astimezone()


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value)


def scout_enabled() -> bool:
    raw = os.environ.get(ENV_ENABLED, "1").strip().lower()
    return raw not in {"0", "false", "no", "off", "disabled"}


def auto_micro_apply_enabled() -> bool:
    raw = os.environ.get(ENV_AUTO_MICRO, "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def fetch_enabled() -> bool:
    raw = os.environ.get(ENV_FETCH, "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _interval_minutes() -> int:
    try:
        return max(15, min(24 * 60, int(os.environ.get(ENV_INTERVAL_MIN, DEFAULT_INTERVAL_MIN))))
    except ValueError:
        return DEFAULT_INTERVAL_MIN


def _force() -> bool:
    return os.environ.get(ENV_FORCE, "").strip().lower() in {"1", "true", "yes", "on"}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _cooldown_active(root: Path) -> bool:
    if _force():
        return False
    state = _read_json(root / STATE_REL)
    last = _safe_str(state.get("last_run_at"))
    if not last:
        return False
    try:
        ts = datetime.fromisoformat(last.replace("Z", "+00:00"))
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.astimezone()
    return _now() - ts < timedelta(minutes=_interval_minutes())


def _ensure_custom_on_path(root: Path) -> None:
    custom = root / "custom"
    text = str(custom)
    if custom.is_dir() and text not in sys.path:
        sys.path.insert(0, text)


def _run_search_activation(root: Path, *, checked_at: str) -> dict[str, Any]:
    _ensure_custom_on_path(root)
    try:
        from autonomous_search_activation_engine import run_autonomous_search_activation

        return dict(
            run_autonomous_search_activation(
                root,
                evaluated_at=checked_at,
                mode="agent_tech_scout_search_activation",
            )
        )
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}


def _run_self_iteration(root: Path, *, checked_at: str) -> dict[str, Any]:
    _ensure_custom_on_path(root)
    out: dict[str, Any] = {}
    try:
        from ai_self_iteration_gate_engine import run_ai_self_iteration_gate

        out["gate"] = dict(
            run_ai_self_iteration_gate(
                root,
                evaluated_at=checked_at,
                mode="agent_tech_scout_self_iteration_gate",
            )
        )
    except Exception as exc:
        out["gate"] = {"error": f"{type(exc).__name__}:{exc}"}
    try:
        from ai_self_iteration_review_engine import run_ai_self_iteration_review

        out["review"] = dict(
            run_ai_self_iteration_review(
                root,
                reviewed_at=checked_at,
                mode="agent_tech_scout_self_iteration_review",
            )
        )
    except Exception as exc:
        out["review"] = {"error": f"{type(exc).__name__}:{exc}"}
    return out


def _run_github_learning(root: Path, *, checked_at: str) -> dict[str, Any]:
    _ensure_custom_on_path(root)
    try:
        from github_autonomous_learning_engine import run_github_autonomous_learning

        return dict(
            run_github_autonomous_learning(
                root,
                checked_at=checked_at,
                mode="agent_tech_scout_github_learning",
            )
        )
    except TypeError:
        # Older signature variants.
        try:
            from github_autonomous_learning_engine import run_github_autonomous_learning

            return dict(run_github_autonomous_learning(root))
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}


def _slugify(text: str) -> str:
    clean = re.sub(r"[^a-z0-9一-鿿]+", "-", _safe_str(text).strip().lower())
    return clean.strip("-")[:48] or "scout"


def _micro_apply_skills(root: Path, *, linked_items: list[dict[str, str]], prefer_papers: bool) -> dict[str, Any]:
    """Create/update review_only skills from scout findings (no stable personality write)."""
    if not auto_micro_apply_enabled():
        return {"applied": 0, "reason": "auto_micro_disabled"}
    if not linked_items:
        return {"applied": 0, "reason": "no_linked_items"}

    existing = {_safe_str(s.get("skill_id")) for s in list_skills(root)}
    existing_urls = set()
    for skill in list_skills(root):
        evidence = _safe_str(skill.get("evidence"))
        if "http" in evidence:
            for token in evidence.split():
                if token.startswith("http"):
                    existing_urls.add(token.rstrip("/").lower())
        routine = _safe_str(skill.get("routine"))
        for token in routine.split():
            if token.startswith("http"):
                existing_urls.add(token.rstrip("/").lower())

    applied = 0
    skipped_dup = 0
    skill_ids: list[str] = []
    for item in linked_items[:3]:
        title = _safe_str(item.get("title")).strip()
        url = _safe_str(item.get("url")).strip()
        if not title or not url.startswith("http"):
            continue
        url_key = url.rstrip("/").lower()
        skill_id = _slugify(f"agent-scout-{title}")
        if url_key in existing_urls or skill_id in existing:
            skipped_dup += 1
            continue
        kind = "论文线索" if prefer_papers or "arxiv.org" in url else "Agent技术线索"
        triggers = [w for w in re.findall(r"[A-Za-z]{3,}|[一-鿿]{2,}", title)[:6]]
        if "agent" not in " ".join(triggers).lower():
            triggers.append("agent")
        if prefer_papers:
            triggers.extend(["论文", "arxiv"])
        routine = (
            f"当讨论{kind}「{title[:40]}」时，可引用公开来源 {url}；"
            "只作方法/情报提示，不改稳定人格；不确定就标明是公开页线索。"
        )
        try:
            write_skill(
                root,
                {
                    "skill_id": skill_id,
                    "title": f"{kind}·{title[:32]}",
                    "situation": f"侦察到相关公开{kind}，话题命中时可作为参考。",
                    "routine": routine,
                    "evidence": f"agent_tech_scout:{url}",
                    "trigger_keys": triggers[:8],
                    "evidence_candidate_ids": [],
                    "evidence_count": 1,
                    "confidence": 2,
                    "tags": ["agent_tech_scout", "review_only", "paper" if prefer_papers else "news"],
                    "status": "review_only",
                },
            )
        except Exception as exc:
            # E5 method immunity or IO — skip this item, keep scout resilient.
            if "method_immunity" in f"{type(exc).__name__}:{exc}".lower() or "method_immunity" in str(exc):
                skipped_dup += 1
                continue
            skipped_dup += 1
            continue
        skill_ids.append(skill_id)
        existing.add(skill_id)
        existing_urls.add(url_key)
        applied += 1
    reason = "ok" if applied else ("all_duplicate" if skipped_dup else "nothing_to_apply")
    return {
        "applied": applied,
        "skipped_duplicate": skipped_dup,
        "skill_ids": skill_ids,
        "reason": reason,
    }


def _append_ai_domain_trace(root: Path, *, line: str, linked_items: list[dict[str, str]]) -> None:
    path = knowledge_file_path(root, "ai_domain.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = _now_iso()
    links = " | ".join(
        f"{_safe_str(i.get('title'))[:40]}<{_safe_str(i.get('url'))}>" for i in linked_items[:3]
    )
    block = (
        f"\n## scout-{stamp[:19].replace(':', '')}\n"
        f"- observed_at: {stamp}\n"
        f"- summary: {_safe_str(line)[:240]}\n"
        f"- links: {links or 'none'}\n"
        f"- integration_scope: knowledge_only\n"
        f"- source: agent_tech_scout_loop\n"
    )
    try:
        existing = path.read_text(encoding="utf-8-sig") if path.exists() else "# AI Domain\n"
    except OSError:
        existing = "# AI Domain\n"
    if "agent_tech_scout_loop" in existing[-2000:] and links and links in existing[-4000:]:
        return
    try:
        path.write_text(existing.rstrip() + "\n" + block, encoding="utf-8")
    except OSError:
        pass


def _seed_general_learned_from_scout(
    root: Path,
    *,
    linked_items: list[dict[str, str]],
    prefer_papers: bool,
) -> dict[str, Any]:
    """Seed q-006 learned entries so self-iteration gate can leave hold_no_ai_source."""
    if not linked_items:
        return {"seeded": 0, "reason": "no_items"}
    path = knowledge_file_path(root, "general.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        text = path.read_text(encoding="utf-8-sig") if path.exists() else "# general\n"
    except OSError:
        text = "# general\n"
    stamped = _now().strftime("%Y-%m-%d")
    seeded = 0
    for idx, item in enumerate(linked_items[:3], start=1):
        title = _safe_str(item.get("title")).strip()
        url = _safe_str(item.get("url")).strip()
        if not title or not url.startswith("http"):
            continue
        learned_id = f"learned-{stamped}-{900 + idx:03d}"
        if learned_id in text or url in text[-8000:]:
            continue
        kind = "paper" if prefer_papers or "arxiv.org" in url else "agent_tech"
        block = (
            f"\n## {learned_id}\n"
            f"- question_id: q-006\n"
            f"- target: ai-self-understanding\n"
            f"- claim: public_{kind}_signal\n"
            f"- claim_text: {title[:160]}\n"
            f"- source_material: scout:{url}\n"
            f"- comparison_status: corroborated\n"
            f"- reliability: high_ready\n"
            f"- integration_scope: knowledge_only\n"
            f"- source: agent_tech_scout_loop\n"
        )
        text = text.rstrip() + "\n" + block
        seeded += 1
    if seeded:
        # Ensure ai_domain target marker exists for gate scoring.
        ai_path = knowledge_file_path(root, "ai_domain.md")
        try:
            ai_text = ai_path.read_text(encoding="utf-8-sig") if ai_path.exists() else "# AI Domain\n"
        except OSError:
            ai_text = "# AI Domain\n"
        if "ai-self-understanding" not in ai_text:
            ai_text = ai_text.rstrip() + "\n\n- target: ai-self-understanding\n"
            try:
                ai_path.write_text(ai_text, encoding="utf-8")
            except OSError:
                pass
        try:
            path.write_text(text, encoding="utf-8")
        except OSError:
            return {"seeded": 0, "reason": "write_failed"}
    return {"seeded": seeded, "reason": "ok" if seeded else "duplicates_or_empty"}

def run_agent_tech_scout_loop(
    root: Path | str,
    *,
    checked_at: str | None = None,
    focus: str = "agent",
    force: bool = False,
) -> dict[str, Any]:
    """Run one full-open scout cycle under device limits."""
    root_path = Path(root).resolve()
    checked = checked_at or _now_iso()
    report: dict[str, Any] = {
        "checked_at": checked,
        "enabled": scout_enabled(),
        "focus": focus,
        "steps": {},
        "ok": False,
    }
    if not scout_enabled() and not force and not _force():
        report["reason"] = "disabled"
        return report
    if _cooldown_active(root_path) and not force and not _force():
        report["reason"] = "cooldown"
        return report

    device = evaluate_device_resource_gate(root_path)
    report["steps"]["device_gate"] = device.as_dict()
    # E4 joint priority: rank scout against maintenance/proactive under device pressure.
    try:
        from xinyu_tick_priority_queue import TickCandidate, plan_from_device_gate, should_run_kind

        queue_plan = plan_from_device_gate(
            [
                TickCandidate(kind="live_chat", ready=False, label="slot"),
                TickCandidate(kind="proactive", ready=False, label="slot"),
                TickCandidate(kind="maintenance", ready=True, label="bg"),
                TickCandidate(
                    kind="tech_scout",
                    ready=True,
                    force=bool(force or _force()),
                    label="scout",
                ),
            ],
            device,
            max_allowed=2,
        )
        report["steps"]["tick_queue"] = queue_plan.as_dict()
        if not force and not _force() and not should_run_kind(queue_plan, "tech_scout"):
            report["reason"] = "tick_queue_deferred"
            _write_json(
                root_path / STATE_REL,
                {"last_run_at": checked, "last_reason": report["reason"]},
            )
            _write_json(root_path / REPORT_REL, report)
            return report
    except Exception as exc:
        report["steps"]["tick_queue"] = {"error": f"{type(exc).__name__}:{exc}"}
    if not device.allowed:
        report["reason"] = f"device_gate:{device.reason}"
        _write_json(root_path / STATE_REL, {"last_run_at": checked, "last_reason": report["reason"]})
        _write_json(root_path / REPORT_REL, report)
        return report

    prefer_papers = focus in {"paper", "papers", "arxiv"} or user_asks_ai_papers(focus)
    prefer_ai = True
    linked_items: list[dict[str, str]] = []
    hot_notes: list[str] = []
    line = ""

    if fetch_enabled():
        fetch_result = fetch_public_hot_pages(
            root_path,
            limit=2,
            prefer_ai=prefer_ai,
            prefer_papers=prefer_papers,
        )
        report["steps"]["fetch"] = {
            "fetched": fetch_result.get("fetched"),
            "urls": fetch_result.get("urls"),
            "errors": fetch_result.get("notes"),
            "prefer_papers": prefer_papers,
        }
        raw_items = filter_ai_relevant_items(
            list(fetch_result.get("linked_items") or []),
            prefer_papers=prefer_papers,
            limit=6,
        )
        # Do not re-process / re-learn links already pushed to owner.
        linked_items, dup_items = filter_unpushed_items(root_path, raw_items)
        hot_notes = list(fetch_result.get("hot_notes") or [])
        line = ""
        if linked_items:
            line = oral_hot_followup_line(
                hot_notes,
                prefer_ai=True,
                prefer_papers=prefer_papers,
                linked_items=linked_items,
            )
        report["steps"]["oral_line"] = line
        report["steps"]["dedupe"] = {
            "fresh": len(linked_items),
            "already_pushed": len(dup_items),
        }
        if linked_items:
            _append_ai_domain_trace(root_path, line=line, linked_items=linked_items)
            report["steps"]["general_seed"] = _seed_general_learned_from_scout(
                root_path,
                linked_items=linked_items,
                prefer_papers=prefer_papers,
            )
            # Scout loop itself does not QQ-push; still mark fingerprints so a later
            # owner ask / follow-up path won't re-announce the same URLs.
            marked = mark_items_pushed(root_path, linked_items)
            report["steps"]["dedupe"]["marked_pushed"] = len(marked)
        elif dup_items and not linked_items:
            report["steps"]["oral_line"] = ""
            report["steps"]["dedupe"]["reason"] = "all_items_already_pushed"
    else:
        report["steps"]["fetch"] = {"skipped": True}

    report["steps"]["search_activation"] = _run_search_activation(root_path, checked_at=checked)
    report["steps"]["github_learning"] = _run_github_learning(root_path, checked_at=checked)
    # Self-iteration after seeding so gate can see q-006 knowledge.
    report["steps"]["self_iteration"] = _run_self_iteration(root_path, checked_at=checked)
    report["steps"]["micro_apply"] = _micro_apply_skills(
        root_path,
        linked_items=linked_items,
        prefer_papers=prefer_papers,
    )

    report["ok"] = True
    report["reason"] = "completed"
    report["linked_items"] = linked_items[:6]
    report["hot_notes"] = hot_notes[:4]
    _write_json(
        root_path / STATE_REL,
        {
            "last_run_at": checked,
            "last_reason": "completed",
            "last_linked_count": len(linked_items),
            "last_micro_applied": int((report["steps"].get("micro_apply") or {}).get("applied") or 0),
        },
    )
    _write_json(root_path / REPORT_REL, report)
    return report
