from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    xinyu_dir = Path(__file__).resolve().parent
    custom_dir = xinyu_dir / "custom"
    sys.path.insert(0, str(custom_dir))

    from inner_framework_manifest import DETERMINISTIC_SYNC_ORDER, INNER_FRAMEWORK_LAYERS

    missing: list[str] = []
    total_files = 0
    layer_names: list[str] = []

    for layer in INNER_FRAMEWORK_LAYERS:
        layer_name = str(layer["name"])
        layer_names.append(layer_name)
        files = [str(item) for item in layer["files"]]
        for rel in files:
            total_files += 1
            if not (xinyu_dir / rel).exists():
                missing.append(rel)

    duplicated_sync_targets = sorted(
        {item for item in DETERMINISTIC_SYNC_ORDER if DETERMINISTIC_SYNC_ORDER.count(item) > 1}
    )

    if missing:
        print("Inner framework validation failed.")
        print("Missing files:")
        for item in missing:
            print(f"- {item}")
        return 1

    if duplicated_sync_targets:
        print("Inner framework validation failed.")
        print("Duplicated deterministic sync targets:")
        for item in duplicated_sync_targets:
            print(f"- {item}")
        return 1

    print("Xinyu inner framework validation passed.")
    print(f"Layers checked: {len(layer_names)}")
    print(f"Files checked: {total_files}")
    print(f"Deterministic sync targets: {len(DETERMINISTIC_SYNC_ORDER)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
