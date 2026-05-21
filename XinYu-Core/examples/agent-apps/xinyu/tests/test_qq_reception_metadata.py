from __future__ import annotations

from xinyu_qq_gateway_utils import hash_id
from xinyu_qq_reception_metadata import (
    annotate_dispatch_reception_metadata,
    annotate_prepared_reception_metadata,
)


def test_annotate_prepared_reception_metadata_sets_ordering_fields() -> None:
    payload: dict[str, object] = {"metadata": {"existing": "kept"}}

    metadata = annotate_prepared_reception_metadata(
        payload,
        event_message_id="m1",
        arrival_seq=2,
        prepared_seq=3,
        session_queue_key="private:42",
    )

    assert metadata["existing"] == "kept"
    assert metadata["qq_arrival_seq"] == 2
    assert metadata["qq_prepared_seq"] == 3
    assert metadata["qq_session_queue_hash"] == hash_id("private:42")
    assert metadata["qq_gateway_received_message_id"] == "m1"
    assert payload["metadata"] is metadata


def test_annotate_dispatch_reception_metadata_creates_metadata_when_missing() -> None:
    payload: dict[str, object] = {}

    metadata = annotate_dispatch_reception_metadata(payload, dispatch_seq=4)

    assert metadata == {"qq_dispatch_seq": 4}
    assert payload["metadata"] is metadata
