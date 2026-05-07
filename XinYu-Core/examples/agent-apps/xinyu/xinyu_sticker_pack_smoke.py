from __future__ import annotations

import os
import shutil
from contextlib import contextmanager
from pathlib import Path

from xinyu_qq_outbox import claim_next_qq_outbox_message
from xinyu_sticker_pack import (
    decide_sticker,
    list_sticker_candidates,
    maybe_enqueue_sticker_reply,
    mood_dir_name,
    select_or_create_sticker,
)


@contextmanager
def _smoke_root(name: str):
    root = Path(__file__).resolve().parent / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    old_scope = os.environ.get("XINYU_LOCAL_SCOPE_DIR")
    old_disable_shared = os.environ.get("XINYU_STICKER_DISABLE_SHARED_ASSET_LIBRARY")
    old_explicit_only = os.environ.get("XINYU_STICKER_EXPLICIT_ONLY")
    old_cooldown = os.environ.get("XINYU_STICKER_AUTO_COOLDOWN_MINUTES")
    os.environ["XINYU_LOCAL_SCOPE_DIR"] = str(root / "local_scope")
    os.environ["XINYU_STICKER_DISABLE_SHARED_ASSET_LIBRARY"] = "1"
    os.environ["XINYU_STICKER_EXPLICIT_ONLY"] = "0"
    os.environ["XINYU_STICKER_AUTO_COOLDOWN_MINUTES"] = "5"
    try:
        yield root
    finally:
        if old_scope is None:
            os.environ.pop("XINYU_LOCAL_SCOPE_DIR", None)
        else:
            os.environ["XINYU_LOCAL_SCOPE_DIR"] = old_scope
        if old_disable_shared is None:
            os.environ.pop("XINYU_STICKER_DISABLE_SHARED_ASSET_LIBRARY", None)
        else:
            os.environ["XINYU_STICKER_DISABLE_SHARED_ASSET_LIBRARY"] = old_disable_shared
        if old_explicit_only is None:
            os.environ.pop("XINYU_STICKER_EXPLICIT_ONLY", None)
        else:
            os.environ["XINYU_STICKER_EXPLICIT_ONLY"] = old_explicit_only
        if old_cooldown is None:
            os.environ.pop("XINYU_STICKER_AUTO_COOLDOWN_MINUTES", None)
        else:
            os.environ["XINYU_STICKER_AUTO_COOLDOWN_MINUTES"] = old_cooldown
        shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    failures: list[str] = []
    with _smoke_root(".sticker_pack_smoke_runtime") as root:
        decision = decide_sticker("心玉，来个表情包")
        if not decision.should_send:
            failures.append("sticker request was not detected")
        if decide_sticker("表情包怎么做？").should_send:
            failures.append("question-only sticker mention was treated as send request")
        os.environ["XINYU_STICKER_EXPLICIT_ONLY"] = "1"
        if decide_sticker("哈哈哈哈好耶太可爱了", "我也乐了").should_send:
            failures.append("explicit-only mode should block automatic stickers")
        if not decide_sticker("心玉，来个表情包").should_send:
            failures.append("explicit-only mode should keep explicit sticker requests working")
        os.environ["XINYU_STICKER_EXPLICIT_ONLY"] = "0"

        sticker_path, notes = select_or_create_sticker(root, mood=decision.mood, seed="smoke")
        if not sticker_path.is_file() or sticker_path.suffix.lower() != ".png":
            failures.append(f"text sticker was not generated: {sticker_path} {notes}")

        payload = {
            "message_type": "private_text",
            "user_id": "42",
            "group_id": None,
            "metadata": {"is_owner_user": True},
        }
        queued = maybe_enqueue_sticker_reply(
            root,
            payload,
            user_text="心玉，来个表情包",
            reply="收到",
            session_key="qq:private:42",
            turn_id="turn-smoke",
        )
        if not queued.get("queued"):
            failures.append(f"sticker outbox enqueue failed: {queued}")
        claim = claim_next_qq_outbox_message(root, {"claim_id": "sticker-claim", "adapter": "smoke"})
        if not claim.get("message_claimed"):
            failures.append("queued sticker was not claimed")
        if claim.get("message_type") != "image":
            failures.append("queued sticker was not an image outbox item")
        if not Path(str(claim.get("image_path"))).is_file():
            failures.append("claimed sticker image path is not a file")
        claim_metadata = claim.get("metadata") if isinstance(claim.get("metadata"), dict) else {}
        if claim_metadata.get("source_turn_id") != "turn-smoke" or not claim_metadata.get("sticker_mood_label"):
            failures.append(f"sticker outbox metadata did not carry self-awareness context: {claim_metadata}")

        happy_dir = root / "emotions" / "stickers" / "happy"
        happy_dir.mkdir(parents=True, exist_ok=True)
        semantic_image = happy_dir / "ha-good.png"
        semantic_alt_image = happy_dir / "ha-good-alt.png"
        try:
            from PIL import Image

            Image.new("RGB", (32, 32), "#ff88aa").save(semantic_image)
            Image.new("RGB", (32, 32), "#88c7ff").save(semantic_alt_image)
        except Exception:
            semantic_image.write_bytes(b"not-a-real-png-but-local-suffix-is-enough-for-outbox")
            semantic_alt_image.write_bytes(b"not-a-real-png-but-local-suffix-is-enough-for-outbox")
        manifest = root / "emotions" / "stickers" / "manifest.json"
        manifest.write_text(
            """
{
  "version": 1,
  "stickers": [
    {
      "file": "happy/ha-good.png",
      "mood": "happy",
      "meaning": "开心、好耶、轻松地一起笑",
      "keywords": ["哈哈", "好耶", "可爱"],
      "auto_send": true,
      "weight": 2
    },
    {
      "file": "happy/ha-good-alt.png",
      "mood": "happy",
      "meaning": "开心、好耶、轻松地一起笑",
      "keywords": ["哈哈", "好耶", "可爱"],
      "auto_send": true,
      "weight": 2
    }
  ]
}
""".strip(),
            encoding="utf-8",
        )
        candidates = list_sticker_candidates(root)
        if not any(item.path == semantic_image.resolve() and item.mood == "happy" for item in candidates):
            failures.append("semantic sticker manifest was not indexed")
        repeated_choice, repeated_notes = select_or_create_sticker(
            root,
            mood="happy",
            seed="avoid-repeat",
            context="haha good cute",
            require_existing=True,
            require_semantic=True,
            auto_only=True,
            avoid_path=semantic_image,
        )
        if repeated_choice.resolve() == semantic_image.resolve():
            failures.append(f"repeat avoidance selected the previous sticker again: {repeated_notes}")
        cute_dir = root / "emotions" / "stickers" / mood_dir_name("cute")
        cute_dir.mkdir(parents=True, exist_ok=True)
        cute_image = cute_dir / "贴贴.png"
        cute_image.write_bytes(b"fake png")
        chinese_candidates = list_sticker_candidates(root)
        if not any(item.path == cute_image.resolve() and item.mood == "cute" for item in chinese_candidates):
            failures.append("Chinese mood folder was not canonicalized")

        auto_decision = decide_sticker("哈哈哈哈好耶太可爱了", "我也乐了")
        if not auto_decision.should_send or auto_decision.mode != "semantic_auto":
            failures.append(f"high-signal chat did not trigger semantic auto sticker: {auto_decision}")
        blocked_auto = decide_sticker("哈哈但是构建失败了", "我先看错误")
        if blocked_auto.should_send:
            failures.append("serious failure context should block auto sticker")

        auto_queued = maybe_enqueue_sticker_reply(
            root,
            payload,
            user_text="哈哈哈哈好耶太可爱了",
            reply="我也乐了",
            session_key="qq:private:42",
            turn_id="turn-auto",
        )
        if not auto_queued.get("queued") or auto_queued.get("mode") != "semantic_auto":
            failures.append(f"semantic auto sticker enqueue failed: {auto_queued}")
        cooled_down = maybe_enqueue_sticker_reply(
            root,
            payload,
            user_text="哈哈哈哈好耶太可爱了",
            reply="我也乐了",
            session_key="qq:private:42",
            turn_id="turn-auto-2",
        )
        if cooled_down.get("queued") or not any("auto_cooldown" in note for note in cooled_down.get("notes", [])):
            failures.append(f"semantic auto sticker cooldown did not engage: {cooled_down}")

    if failures:
        print("xinyu_sticker_pack_smoke: failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("xinyu_sticker_pack_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
