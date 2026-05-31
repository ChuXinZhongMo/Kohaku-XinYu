from __future__ import annotations

from xinyu_voice_style_sampler import (
    analyse_style_samples,
    collect_public_style_samples,
    derive_proactive_constraints,
    infer_proactive_scene,
    proactive_scene_templates,
    write_style_sample_report,
)


def test_sampler_collects_safe_public_style_signals():
    samples = collect_public_style_samples()
    analysis = analyse_style_samples(samples)

    assert analysis["sample_count"] >= 90
    assert analysis["corpus_finding_count"] >= 7
    assert analysis["length_buckets"]["short"] > analysis["length_buckets"]["long"]
    assert analysis["question_like_count"] >= 8
    assert analysis["contextual_ratio"] > 0.25
    assert analysis["scene_counts"]
    assert all("傻逼" not in sample["text"] for sample in samples)


def test_sampler_derives_proactive_constraints_from_analysis():
    samples = collect_public_style_samples()
    analysis = analyse_style_samples(samples)
    constraints = derive_proactive_constraints(analysis)
    text = "\n".join(constraints)

    assert "4-14" in text
    assert "刚才那个" in text
    assert "请确认" in text


def test_sampler_provides_scene_templates_for_proactive_voice():
    assert infer_proactive_scene("要不要我继续接上刚才那块？") == "继续/收束"
    assert infer_proactive_scene("那我先不打扰你") == "不打扰"
    assert "那我接着？" in proactive_scene_templates("继续/收束", "那块")
    assert "那我先不吵你" in proactive_scene_templates("不打扰", "这个")



def test_write_style_sample_report_keeps_memory_boundaries(tmp_path):
    path = write_style_sample_report(tmp_path, updated_at="2026-05-24T00:00:00+00:00")
    text = path.read_text(encoding="utf-8")

    assert path.relative_to(tmp_path).as_posix() == "memory/self/voice_style_sample_report.md"
    assert "public_aggregate_style_sampling_only" in text
    assert "stable_persona_write: blocked" in text
    assert "owner_memory_write: blocked" in text
    assert "raw_private_body_retained: false" in text
    assert "Derived proactive constraints" in text
    assert "Safe sampled pattern examples" in text
