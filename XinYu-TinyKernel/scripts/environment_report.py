from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> dict[str, object]:
    exe = shutil.which(cmd[0])
    if not exe:
        return {"available": False, "error": "not_found"}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except Exception as exc:
        return {"available": True, "error": f"{type(exc).__name__}: {exc}"}
    return {"available": True, "returncode": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}


def torch_info() -> dict[str, object]:
    try:
        import torch
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    info: dict[str, object] = {
        "available": True,
        "version": getattr(torch, "__version__", ""),
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_version": getattr(torch.version, "cuda", ""),
        "device_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
    }
    if torch.cuda.is_available():
        devices = []
        for idx in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(idx)
            devices.append({"index": idx, "name": props.name, "total_memory_gb": round(props.total_memory / (1024**3), 2)})
        info["devices"] = devices
    return info


def package_available(name: str) -> dict[str, object]:
    try:
        module = __import__(name)
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"available": True, "version": getattr(module, "__version__", "")}


def main() -> int:
    report = {
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "torch": torch_info(),
        "transformers": package_available("transformers"),
        "peft": package_available("peft"),
        "trl": package_available("trl"),
        "accelerate": package_available("accelerate"),
        "nvidia_smi": run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"]),
    }
    out = ROOT / "data" / "raw_index" / "environment_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps(report["torch"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
