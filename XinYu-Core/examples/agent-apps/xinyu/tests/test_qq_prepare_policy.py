from __future__ import annotations

from xinyu_qq_prepare_policy import (
    basic_channel_reject_reason,
    codex_command_scope_reject_reason,
    empty_message_reason,
    owner_private_command_reject_reason,
    package_install_scope_reject_reason,
    sticker_import_scope_reject_reason,
)


def test_empty_message_reason() -> None:
    assert empty_message_reason(text="", learning_material=None, sticker_material=None, rich_segments=None) == "empty_message"
    assert (
        empty_message_reason(text="", learning_material=None, sticker_material=None, rich_segments=[{"k": 1}])
        == "rich_message_without_supported_route"
    )
    assert empty_message_reason(text="hi", learning_material=None, sticker_material=None, rich_segments=None) is None


def test_sticker_and_package_and_codex_scope() -> None:
    owners = frozenset({"owner"})
    assert (
        sticker_import_scope_reject_reason(
            enabled=True,
            private_owner_only=True,
            message_kind="group",
            sender_id="owner",
            owner_user_ids=owners,
            has_sticker_material=True,
        )
        == "sticker_import_private_owner_only"
    )
    assert (
        package_install_scope_reject_reason(
            package_text="install foo",
            enabled=False,
            owner_private_only=True,
            message_kind="private",
            sender_id="owner",
            owner_user_ids=owners,
        )
        == "package_install_disabled"
    )
    assert (
        codex_command_scope_reject_reason(
            codex_task="do thing",
            enabled=True,
            message_kind="group",
            sender_id="owner",
            owner_user_ids=owners,
        )
        == "codex_private_only"
    )
    assert (
        codex_command_scope_reject_reason(
            codex_task="do thing",
            enabled=True,
            message_kind="private",
            sender_id="stranger",
            owner_user_ids=owners,
        )
        == "codex_owner_only"
    )
    assert basic_channel_reject_reason(
        private_only=True, message_kind="group", allow_group_messages=True
    ) == "private_only"
    assert basic_channel_reject_reason(
        private_only=False, message_kind="group", allow_group_messages=False
    ) == "group_disabled"
    assert (
        owner_private_command_reject_reason(
            message_kind="group",
            sender_id="owner",
            owner_user_ids=owners,
        )
        == "owner_private_only"
    )
    assert (
        owner_private_command_reject_reason(
            message_kind="private",
            sender_id="owner",
            owner_user_ids=owners,
        )
        is None
    )
    from xinyu_qq_prepare_policy import learning_ingest_scope_reject_reason

    assert learning_ingest_scope_reject_reason(
        enabled=True,
        has_learning_material=True,
        file_learning_reject_reason="file_learning_private_owner_only",
    ) == "file_learning_private_owner_only"
    assert (
        learning_ingest_scope_reject_reason(
            enabled=True,
            has_learning_material=True,
            file_learning_reject_reason="",
        )
        is None
    )
