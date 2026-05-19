from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LENSES = ("warmth", "attachment", "hurt", "irritation", "fatigue", "stability")


def main() -> int:
    for lens in LENSES:
        config = {
            "assistant_only_loss": True,
            "base_model": r"D:\XinYu\XinYu-TinyKernel\models\Qwen2.5-0.5B-Instruct",
            "batch_size": 1,
            "bf16": False,
            "dataset_eval": f"data/sft/emotion_{lens}_eval_v002.jsonl",
            "dataset_train": f"data/sft/emotion_{lens}_train_v002.jsonl",
            "epochs": 2,
            "fp16": True,
            "gradient_accumulation_steps": 8,
            "gradient_checkpointing": False,
            "learning_rate": 0.00008,
            "lora_alpha": 16,
            "lora_dropout": 0.05,
            "lora_r": 8,
            "max_seq_length": 512,
            "method": "lora_persona_emotion_bias_masked",
            "output_dir": f"adapters/emotion_{lens}_v002",
            "role": f"emotion_{lens}",
            "save_steps": 50,
            "status": "approved_for_training",
        }
        path = ROOT / "configs" / f"train_emotion_{lens}_v002.json"
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
