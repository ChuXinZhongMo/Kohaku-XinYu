from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

import base64
import shutil
from contextlib import contextmanager
from pathlib import Path

import xinyu_qq_outbox as outbox_module
from xinyu_qq_outbox import (
    ack_qq_outbox_message,
    claim_next_qq_outbox_message,
    enqueue_owner_qq_outbox_file,
    enqueue_owner_qq_outbox_image,
    enqueue_qq_outbox_file,
    enqueue_qq_outbox_image,
    enqueue_qq_outbox_message,
)


MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


@contextmanager
def _smoke_root(name: str):
    root = Path(__file__).resolve().parent / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    failures: list[str] = []
    with _smoke_root(".qq_outbox_smoke_runtime") as root:
        queued = enqueue_qq_outbox_message(
            root,
            user_id="42",
            message="Codex 跑完了。报告在本地 Codex Outbox：codex-qq-smoke-report.md。",
            source="codex_completion",
            dedupe_key="codex_completion:smoke",
            metadata={"job_id": "smoke"},
        )
        if not queued.get("queued"):
            failures.append("message was not queued")

        duplicate = enqueue_qq_outbox_message(
            root,
            user_id="42",
            message="duplicate",
            source="codex_completion",
            dedupe_key="codex_completion:smoke",
        )
        if duplicate.get("queued") or "duplicate_dedupe_key" not in duplicate.get("notes", []):
            failures.append("dedupe did not block duplicate message")

        claim = claim_next_qq_outbox_message(root, {"claim_id": "claim-1", "adapter": "smoke"})
        if not claim.get("message_claimed"):
            failures.append("queued message was not claimed")
        if claim.get("target", {}).get("message_kind") != "private":
            failures.append("claimed target is not private")
        if "D:\\XinYu" in str(claim.get("message", "")):
            failures.append("claimed message leaked a raw local path")

        empty = claim_next_qq_outbox_message(root, {"claim_id": "claim-empty", "adapter": "smoke"})
        if empty.get("message_claimed"):
            failures.append("claimed same message twice before ack")

        ack = ack_qq_outbox_message(
            root,
            {
                "message_id": claim.get("message_id"),
                "claim_id": claim.get("claim_id"),
                "ack_status": "sent",
                "adapter_message_id": "qq-msg-1",
            },
        )
        if not ack.get("ack_recorded") or ack.get("ack_status") != "sent":
            failures.append("sent ack was not recorded")

        after_sent = claim_next_qq_outbox_message(root, {"claim_id": "claim-after-sent", "adapter": "smoke"})
        if after_sent.get("message_claimed"):
            failures.append("sent message was claimed again")

        image_path = root / "owner-preview.png"
        image_path.write_bytes(MINIMAL_PNG)
        image_queued = enqueue_qq_outbox_image(
            root,
            user_id="42",
            image_path=str(image_path),
            caption="preview ready",
            source="image_dispatch_smoke",
            dedupe_key="image_dispatch:smoke",
            metadata={"job_id": "image-smoke"},
        )
        if not image_queued.get("queued"):
            failures.append(f"image message was not queued: {image_queued}")

        image_claim = claim_next_qq_outbox_message(root, {"claim_id": "claim-image", "adapter": "smoke"})
        if not image_claim.get("message_claimed"):
            failures.append("queued image was not claimed")
        if image_claim.get("message_type") != "image":
            failures.append("claimed image message did not carry message_type=image")
        if image_claim.get("image_path") != str(image_path.resolve()):
            failures.append("claimed image path did not match normalized local file")
        if str(image_path) in str(image_claim.get("message", "")):
            failures.append("image caption leaked the raw local path")

        image_ack = ack_qq_outbox_message(
            root,
            {
                "message_id": image_claim.get("message_id"),
                "claim_id": image_claim.get("claim_id"),
                "ack_status": "sent",
                "adapter_message_id": "qq-img-1",
            },
        )
        if not image_ack.get("ack_recorded") or image_ack.get("ack_status") != "sent":
            failures.append("image sent ack was not recorded")

        file_path = root / "owner-report.txt"
        file_path.write_text("report ready\n", encoding="utf-8")
        file_queued = enqueue_qq_outbox_file(
            root,
            user_id="42",
            file_path=str(file_path),
            name="report.txt",
            caption="report ready",
            source="file_dispatch_smoke",
            dedupe_key="file_dispatch:smoke",
            metadata={"job_id": "file-smoke"},
        )
        if not file_queued.get("queued"):
            failures.append(f"file message was not queued: {file_queued}")

        file_claim = claim_next_qq_outbox_message(root, {"claim_id": "claim-file", "adapter": "smoke"})
        if not file_claim.get("message_claimed"):
            failures.append("queued file was not claimed")
        if file_claim.get("message_type") != "file":
            failures.append("claimed file message did not carry message_type=file")
        if file_claim.get("file_path") != str(file_path.resolve()):
            failures.append("claimed file path did not match normalized local file")
        if file_claim.get("file_name") != "report.txt":
            failures.append("claimed file name did not match requested name")
        if str(file_path) in str(file_claim.get("message", "")):
            failures.append("file caption leaked the raw local path")

        file_ack = ack_qq_outbox_message(
            root,
            {
                "message_id": file_claim.get("message_id"),
                "claim_id": file_claim.get("claim_id"),
                "ack_status": "sent",
                "adapter_message_id": "qq-file-1",
            },
        )
        if not file_ack.get("ack_recorded") or file_ack.get("ack_status") != "sent":
            failures.append("file sent ack was not recorded")

        owner_config = root / "xinyu_qq_gateway.config.json"
        owner_config.write_text('{"owner_user_ids": ["42"]}\n', encoding="utf-8")
        owner_image_queued = enqueue_owner_qq_outbox_image(
            root,
            image_path=str(image_path),
            caption="owner preview ready",
            source="owner_image_dispatch_smoke",
            dedupe_key="owner_image_dispatch:smoke",
            metadata={"job_id": "owner-image-smoke"},
            config_path=owner_config,
        )
        if not owner_image_queued.get("queued"):
            failures.append(f"owner image message was not queued: {owner_image_queued}")

        owner_image_claim = claim_next_qq_outbox_message(root, {"claim_id": "claim-owner-image", "adapter": "smoke"})
        if not owner_image_claim.get("message_claimed"):
            failures.append("queued owner image was not claimed")
        if owner_image_claim.get("target", {}).get("user_id") != "42":
            failures.append("owner image target did not use configured owner")
        if owner_image_claim.get("message_type") != "image":
            failures.append("owner image claim did not carry message_type=image")

        owner_image_ack = ack_qq_outbox_message(
            root,
            {
                "message_id": owner_image_claim.get("message_id"),
                "claim_id": owner_image_claim.get("claim_id"),
                "ack_status": "sent",
                "adapter_message_id": "qq-img-owner-1",
            },
        )
        if not owner_image_ack.get("ack_recorded") or owner_image_ack.get("ack_status") != "sent":
            failures.append("owner image sent ack was not recorded")

        owner_file_queued = enqueue_owner_qq_outbox_file(
            root,
            file_path=str(file_path),
            name="owner-report.txt",
            caption="owner report ready",
            source="owner_file_dispatch_smoke",
            dedupe_key="owner_file_dispatch:smoke",
            metadata={"job_id": "owner-file-smoke"},
            config_path=owner_config,
        )
        if not owner_file_queued.get("queued"):
            failures.append(f"owner file message was not queued: {owner_file_queued}")

        owner_file_claim = claim_next_qq_outbox_message(root, {"claim_id": "claim-owner-file", "adapter": "smoke"})
        if not owner_file_claim.get("message_claimed"):
            failures.append("queued owner file was not claimed")
        if owner_file_claim.get("target", {}).get("user_id") != "42":
            failures.append("owner file target did not use configured owner")
        if owner_file_claim.get("message_type") != "file":
            failures.append("owner file claim did not carry message_type=file")

        owner_file_ack = ack_qq_outbox_message(
            root,
            {
                "message_id": owner_file_claim.get("message_id"),
                "claim_id": owner_file_claim.get("claim_id"),
                "ack_status": "sent",
                "adapter_message_id": "qq-file-owner-1",
            },
        )
        if not owner_file_ack.get("ack_recorded") or owner_file_ack.get("ack_status") != "sent":
            failures.append("owner file sent ack was not recorded")

        state = (root / "memory/context/qq_outbox_dispatch_state.md").read_text(encoding="utf-8")
        for marker in (
            "sent_count: 5",
            "recent_failed_count: 0",
            "recent_dead_count: 0",
            "last_failed_at: none",
            "last_dead_at: none",
            "QQ Outbox Dispatch State",
            "Gateway must ack",
            "Image dispatch may carry",
            "File dispatch may carry",
        ):
            if marker not in state:
                failures.append(f"dispatch state missing marker: {marker}")

        failed_queued = enqueue_qq_outbox_message(
            root,
            user_id="42",
            message="will fail once",
            source="smoke_failure",
            dedupe_key="fail-once",
        )
        failed_claim = claim_next_qq_outbox_message(root, {"claim_id": "claim-failed", "adapter": "smoke"})
        failed_ack = ack_qq_outbox_message(
            root,
            {
                "message_id": failed_claim.get("message_id") or failed_queued.get("message_id"),
                "claim_id": failed_claim.get("claim_id"),
                "ack_status": "failed",
                "adapter_error": "simulated failure",
            },
        )
        if not failed_ack.get("ack_recorded") or failed_ack.get("ack_status") != "failed":
            failures.append("failed ack was not recorded")
        failed_state = (root / "memory/context/qq_outbox_dispatch_state.md").read_text(encoding="utf-8")
        for marker in ("failed_count: 1", "recent_failed_count: 1"):
            if marker not in failed_state:
                failures.append(f"failed dispatch state missing marker: {marker}")
        if "last_failed_at: none" in failed_state:
            failures.append("failed dispatch state did not record last_failed_at")

        control_queued = enqueue_qq_outbox_message(
            root,
            user_id="42",
            message="[Review Inbox] internal command card",
            source="review_inbox",
            dedupe_key="review-control-plane-suppressed",
            metadata={"control_plane": True},
        )
        if not control_queued.get("queued"):
            failures.append(f"control-plane suppression setup was not queued: {control_queued}")
        control_claim = claim_next_qq_outbox_message(root, {"claim_id": "claim-control-plane", "adapter": "smoke"})
        if control_claim.get("message_claimed"):
            failures.append(f"control-plane message should not be claimed for visible QQ delivery: {control_claim}")
        if "control_plane_suppressed:1" not in control_claim.get("notes", []):
            failures.append(f"control-plane suppression note missing: {control_claim}")

        original_replace = outbox_module.os.replace
        attempts = {"count": 0}
        transient_path = root / "memory/context/transient-state.md"

        def flaky_replace(src: str, dst: str) -> None:
            if Path(dst) == transient_path and attempts["count"] == 0:
                attempts["count"] += 1
                raise PermissionError(5, "simulated transient Windows file lock", dst)
            original_replace(src, dst)

        outbox_module.os.replace = flaky_replace
        try:
            outbox_module._atomic_write_text(transient_path, "ok\n")
        finally:
            outbox_module.os.replace = original_replace
        if transient_path.read_text(encoding="utf-8") != "ok\n" or attempts["count"] != 1:
            failures.append("atomic state write did not retry transient PermissionError")

    if failures:
        print("QQ outbox smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("QQ outbox smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

