from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRAIN_CONFIG = ROOT / "configs" / "train.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(TRAIN_CONFIG))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="Run a tiny end-to-end trainer smoke without approving full training.")
    parser.add_argument("--base-model", default="", help="Override base model path or repo id.")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    train_path = ROOT / str(config.get("dataset_train", "data/sft/train_v0.jsonl"))
    eval_path = ROOT / str(config.get("dataset_eval", "data/sft/eval_v0.jsonl"))

    print(f"config={config_path}")
    print(f"train={train_path}")
    print(f"eval={eval_path}")
    base_model = args.base_model or str(config.get("base_model"))
    print(f"base_model={base_model}")
    if not train_path.exists():
        print(f"missing_train_dataset={train_path}")
        return 2
    if not eval_path.exists():
        print(f"missing_eval_dataset={eval_path}")
        return 2

    if args.dry_run:
        print("dry_run_ok=true")
        return 0

    if config.get("status") != "approved_for_training" and not args.smoke:
        print("training_blocked=true")
        print("reason=train.json status is not approved_for_training")
        print("required=manual data review + eval pass + safety scan pass")
        return 2

    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import AutoConfig, AutoModelForCausalLM, AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments
    except Exception as exc:
        print("training_dependencies_missing=true")
        print(f"error={type(exc).__name__}: {exc}")
        print("install_after_review=pip install torch transformers peft accelerate datasets bitsandbytes")
        return 2

    cuda_memory_fraction = config.get("cuda_memory_fraction")
    if cuda_memory_fraction is not None and torch.cuda.is_available():
        fraction = max(0.1, min(float(cuda_memory_fraction), 1.0))
        torch.cuda.set_per_process_memory_fraction(fraction, device=0)
        print(f"cuda_memory_fraction={fraction}")

    bf16_requested = bool(config.get("bf16", False))
    bf16_enabled = bool(bf16_requested and torch.cuda.is_available() and torch.cuda.is_bf16_supported())
    fp16_enabled = bool(config.get("fp16", True) and torch.cuda.is_available() and not bf16_enabled)
    model_dtype = torch.bfloat16 if bf16_enabled else torch.float16 if fp16_enabled else torch.float32
    load_in_4bit = bool(config.get("load_in_4bit", False))

    try:
        tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    except Exception as exc:
        print("model_load_failed=true")
        print(f"error={type(exc).__name__}: {exc}")
        print("hint=Use --base-model <local_path> or set HF_ENDPOINT to a reachable Hugging Face mirror.")
        return 2
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def render_generation_prompt(messages: list[dict[str, Any]]) -> str:
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    try:
        quantization_config = None
        if load_in_4bit:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type=str(config.get("bnb_4bit_quant_type", "nf4")),
                bnb_4bit_compute_dtype=model_dtype if model_dtype in {torch.float16, torch.bfloat16} else torch.float16,
                bnb_4bit_use_double_quant=bool(config.get("bnb_4bit_use_double_quant", True)),
            )
        model_config = AutoConfig.from_pretrained(base_model, trust_remote_code=True)
        model_auto_cls = (
            AutoModelForCausalLM
            if type(model_config) in AutoModelForCausalLM._model_mapping
            else AutoModelForImageTextToText
        )
        print(f"model_auto_class={model_auto_cls.__name__}")
        model = model_auto_cls.from_pretrained(
            base_model,
            torch_dtype=model_dtype,
            device_map="auto" if load_in_4bit else None,
            quantization_config=quantization_config,
            trust_remote_code=True,
        )
    except Exception as exc:
        print("model_load_failed=true")
        print(f"error={type(exc).__name__}: {exc}")
        print("hint=Use --base-model <local_path> or set HF_ENDPOINT to a reachable Hugging Face mirror.")
        return 2
    model.config.use_cache = False
    if load_in_4bit:
        if bool(config.get("skip_kbit_fp32_cast", False)):
            for param in model.parameters():
                param.requires_grad = False
            if bool(config.get("gradient_checkpointing", True)):
                if hasattr(model, "enable_input_require_grads"):
                    model.enable_input_require_grads()
                if hasattr(model, "gradient_checkpointing_enable"):
                    model.gradient_checkpointing_enable()
            print("skip_kbit_fp32_cast=true")
        else:
            model = prepare_model_for_kbit_training(
                model,
                use_gradient_checkpointing=bool(config.get("gradient_checkpointing", True)),
            )

    target_modules = config.get("target_modules")
    if not isinstance(target_modules, list) or not target_modules:
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

    lora_config = LoraConfig(
        r=int(config.get("lora_r", 4)),
        lora_alpha=int(config.get("lora_alpha", 16)),
        lora_dropout=float(config.get("lora_dropout", 0.05)),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[str(item) for item in target_modules],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    max_seq_length = int(config.get("max_seq_length", 512))

    def tokenize_row(row: dict[str, Any]) -> dict[str, list[int]]:
        messages = row.get("messages")
        if not isinstance(messages, list) or len(messages) < 3:
            raise ValueError("row must contain at least 3 chat messages")
        prompt_messages = messages[:-1]
        assistant = messages[-1]
        if not isinstance(assistant, dict):
            raise ValueError("assistant message must be an object")
        assistant_content = str(assistant.get("content", "")).strip()
        prompt = render_generation_prompt(prompt_messages)
        target = assistant_content + (tokenizer.eos_token or "")
        prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        target_ids = tokenizer(target, add_special_tokens=False)["input_ids"]
        if len(target_ids) >= max_seq_length:
            target_ids = target_ids[: max_seq_length - 1] + [tokenizer.eos_token_id]
            prompt_ids = []
        elif len(prompt_ids) + len(target_ids) > max_seq_length:
            prompt_ids = prompt_ids[-(max_seq_length - len(target_ids)) :]
        input_ids = prompt_ids + target_ids
        return {
            "input_ids": input_ids,
            "attention_mask": [1] * len(input_ids),
            "labels": [-100] * len(prompt_ids) + target_ids,
        }

    class CausalCollator:
        def __call__(self, features: list[dict[str, list[int]]]) -> dict[str, torch.Tensor]:
            max_len = max(len(item["input_ids"]) for item in features)
            batch: dict[str, list[list[int]]] = {"input_ids": [], "attention_mask": [], "labels": []}
            pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
            for item in features:
                pad_len = max_len - len(item["input_ids"])
                batch["input_ids"].append(item["input_ids"] + [pad_id] * pad_len)
                batch["attention_mask"].append(item["attention_mask"] + [0] * pad_len)
                batch["labels"].append(item["labels"] + [-100] * pad_len)
            return {key: torch.tensor(value, dtype=torch.long) for key, value in batch.items()}

    dataset = load_dataset("json", data_files={"train": str(train_path), "eval": str(eval_path)})
    if args.smoke:
        dataset["train"] = dataset["train"].select(range(min(12, len(dataset["train"]))))
        dataset["eval"] = dataset["eval"].select(range(min(4, len(dataset["eval"]))))
    tokenized = dataset.map(tokenize_row, remove_columns=dataset["train"].column_names)

    output_dir = ROOT / ("adapters/smoke_lora" if args.smoke else str(config.get("output_dir", "adapters/v001_initial_voice")))
    max_steps = 2 if args.smoke else int(config.get("max_steps", -1))
    logging_steps = int(config.get("logging_steps", 5))
    eval_steps = 2 if args.smoke else int(config.get("eval_steps", 50))
    eval_strategy = str(config.get("eval_strategy", "steps"))

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=int(config.get("batch_size", 1)),
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=int(config.get("gradient_accumulation_steps", 8)),
        num_train_epochs=float(config.get("epochs", 1)),
        max_steps=max_steps,
        learning_rate=float(config.get("learning_rate", 1e-4)),
        logging_steps=logging_steps,
        save_steps=int(config.get("save_steps", 50)),
        eval_strategy=eval_strategy,
        eval_steps=eval_steps,
        optim=str(config.get("optim", "adamw_torch")),
        fp16=fp16_enabled,
        bf16=bf16_enabled,
        gradient_checkpointing=bool(config.get("gradient_checkpointing", False)),
        remove_unused_columns=False,
        report_to=[],
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["eval"],
        data_collator=CausalCollator(),
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print("training_complete=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
