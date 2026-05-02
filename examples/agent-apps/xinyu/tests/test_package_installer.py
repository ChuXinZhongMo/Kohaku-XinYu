from __future__ import annotations

from xinyu_dialogue_working_memory import save_dialogue_tail
from xinyu_package_installer import (
    infer_package_text_from_dialogue,
    parse_package_specs,
)


def test_parse_package_specs_accepts_simple_names() -> None:
    specs = parse_package_specs({"packages": "pypdf PyMuPDF"})

    assert [spec.raw for spec in specs] == ["pypdf", "PyMuPDF"]
    assert [spec.import_name for spec in specs] == ["pypdf", "fitz"]


def test_parse_package_specs_rejects_shell_fragments() -> None:
    try:
        parse_package_specs({"packages": "pypdf; echo nope"})
    except Exception as exc:
        assert "unsafe package spec" in str(exc)
    else:
        raise AssertionError("unsafe package spec was accepted")


def test_infer_package_text_from_dialogue_tail(tmp_path) -> None:
    root = tmp_path / "xinyu"
    save_dialogue_tail(
        root,
        "qq:private:owner",
        [
            {"role": "assistant", "content": "缺 PyMuPDF。终端里跑 pip install pymupdf 就行。"},
            {"role": "user", "content": "帮她装"},
        ],
    )

    inferred = infer_package_text_from_dialogue(
        root,
        {"session_id": "qq:private:owner", "current_text": "帮她装"},
    )

    assert inferred.lower() == "pymupdf"
