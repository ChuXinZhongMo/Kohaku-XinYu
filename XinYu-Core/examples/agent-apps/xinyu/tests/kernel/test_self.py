"""Unit tests for Cognitive Kernel Self (K-001).

Run:
    python -m pytest tests/kernel/test_self.py -q --tb=short
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from kernel.exceptions import OwnershipError
from kernel.self import Self
from kernel.self.persistence import (
    load_self_from_json,
    save_self_to_json,
    self_from_json_string,
    self_to_json_string,
)


def test_self_creates_with_generated_id():
    s = Self()
    assert s.self_id
    assert isinstance(s.self_id, str)
    assert len(s.self_id) > 0


def test_self_can_use_stable_id():
    s = Self(self_id="persistent-self-001")
    assert s.self_id == "persistent-self-001"


def test_claim_and_verify_ownership():
    s = Self(self_id="test-self")
    s.claim_ownership("obj-123", "memory_fragment")
    assert s.verify_ownership("obj-123") is True
    assert s.verify_ownership("nonexistent") is False


def test_cannot_claim_same_object_twice():
    s = Self()
    s.claim_ownership("unique-obj", "belief")
    with pytest.raises(OwnershipError):
        s.claim_ownership("unique-obj", "belief")


def test_get_owned_objects_returns_list():
    s = Self()
    s.claim_ownership("a", "type1")
    s.claim_ownership("b", "type2")
    owned = s.get_owned_objects()
    assert len(owned) == 2
    assert owned[0]["obj_id"] == "a"
    assert owned[1]["obj_type"] == "type2"


def test_release_ownership():
    s = Self()
    s.claim_ownership("temp", "ephemeral")
    assert s.verify_ownership("temp") is True
    released = s.release_ownership("temp")
    assert released is True
    assert s.verify_ownership("temp") is False


def test_to_dict_and_from_dict_roundtrip():
    s1 = Self(self_id="roundtrip-self")
    s1.claim_ownership("mem-1", "memory")
    s1.claim_ownership("fact-7", "fact")

    data = s1.to_dict()
    assert data["self_id"] == "roundtrip-self"
    assert "model" in data

    s2 = Self.from_dict(data)
    assert s2.self_id == s1.self_id
    assert s2.verify_ownership("mem-1") is True
    assert s2.verify_ownership("fact-7") is True
    assert len(s2.get_owned_objects()) == 2


def test_persistence_json_file_roundtrip():
    s1 = Self(self_id="file-self")
    s1.claim_ownership("doc-xyz", "document")

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "self.json"
        save_self_to_json(s1, p)

        s2 = load_self_from_json(p)
        assert s2.self_id == "file-self"
        assert s2.verify_ownership("doc-xyz") is True


def test_json_string_helpers():
    s1 = Self(self_id="string-self")
    s1.claim_ownership("x", "y")

    s = self_to_json_string(s1)
    assert isinstance(s, str)
    data = json.loads(s)
    assert data["self_id"] == "string-self"

    s2 = self_from_json_string(s)
    assert s2.self_id == "string-self"
    assert s2.verify_ownership("x") is True


def test_verify_ownership_with_invalid_input():
    s = Self()
    assert s.verify_ownership("") is False
    assert s.verify_ownership(None) is False  # type: ignore
    assert s.verify_ownership(123) is False  # type: ignore
