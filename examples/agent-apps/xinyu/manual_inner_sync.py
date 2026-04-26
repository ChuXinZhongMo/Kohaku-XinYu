from __future__ import annotations

import argparse
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_sync_module(xinyu_dir: Path):
    sys.path.insert(0, str(xinyu_dir.parents[2] / "src"))
    module_path = xinyu_dir / "custom" / "memory_sync_plugin.py"
    spec = spec_from_file_location("xinyu_memory_sync_plugin_manual", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load sync module from {module_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply Xinyu inner sync without running the full agent.")
    parser.add_argument("--user", required=True, help="User text for the sync turn.")
    parser.add_argument(
        "--assistant",
        default="",
        help="Assistant text for the same turn. Can be empty when validating inner sync only.",
    )
    parser.add_argument(
        "--show-files",
        action="store_true",
        help="Print key inner-framework files after sync.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    xinyu_dir = Path(__file__).resolve().parent
    module = _load_sync_module(xinyu_dir)
    changed = module.sync_from_texts(xinyu_dir, args.user, args.assistant)

    print("Xinyu manual inner sync complete." if changed else "Xinyu manual inner sync skipped.")
    print(f"Meaningful turn: {str(changed).lower()}")
    if args.show_files:
        for rel in [
            "memory/context/inner_sync_state.md",
            "memory/context/continuity_index.md",
            "memory/context/maintenance_targets.md",
            "memory/archive/archive_queue.md",
            "memory/reflection/reflection_queue.md",
            "memory/dreams/dream_seeds.md",
        ]:
            path = xinyu_dir / rel
            print(f"\n--- {rel} ---")
            print(path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
