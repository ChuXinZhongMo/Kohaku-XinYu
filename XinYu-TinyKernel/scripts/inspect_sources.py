from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from common import CONFIG_DIR, DATA_DIR, dump_json, load_json, read_jsonl, rel_to


def inspect_sqlite(path: Path, tables: list[str]) -> dict[str, object]:
    result: dict[str, object] = {"exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0, "tables": {}}
    if not path.exists():
        return result
    con = sqlite3.connect(path)
    try:
        table_info: dict[str, object] = {}
        for table in tables:
            try:
                count = con.execute(f'select count(*) from "{table}"').fetchone()[0]
                columns = [row[1] for row in con.execute(f'pragma table_info("{table}")').fetchall()]
                table_info[table] = {"rows": count, "columns": columns}
            except sqlite3.Error as exc:
                table_info[table] = {"error": str(exc)}
        result["tables"] = table_info
    finally:
        con.close()
    return result


def inspect_jsonl(path: Path) -> dict[str, object]:
    sample = read_jsonl(path, limit=3)
    line_count = 0
    if path.exists():
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            line_count = sum(1 for _ in handle)
    return {
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "lines": line_count,
        "sample_keys": sorted(sample[0].keys()) if sample else [],
    }


def inspect_directory(path: Path, glob: str) -> dict[str, object]:
    files = sorted(path.glob(glob)) if path.exists() else []
    return {
        "exists": path.exists(),
        "files": len(files),
        "bytes": sum(item.stat().st_size for item in files if item.is_file()),
        "sample": [item.name for item in files[:5]],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(CONFIG_DIR / "data_sources.json"))
    parser.add_argument("--out", default=str(DATA_DIR / "raw_index" / "source_manifest.json"))
    args = parser.parse_args()

    config = load_json(Path(args.config))
    xinyu_root = Path(config["xinyu_root"])
    manifest: dict[str, object] = {"xinyu_root": str(xinyu_root), "sources": {}}
    sources: dict[str, object] = {}
    for name, source in config["allowed_sources"].items():
        source_type = source["type"]
        path = rel_to(xinyu_root, source["path"])
        if source_type == "sqlite":
            sources[name] = inspect_sqlite(path, list(source.get("tables", [])))
        elif source_type == "jsonl":
            sources[name] = inspect_jsonl(path)
        elif source_type == "directory":
            sources[name] = inspect_directory(path, str(source.get("glob", "*")))
        else:
            sources[name] = {"error": f"unknown source type: {source_type}"}
    manifest["sources"] = sources
    dump_json(Path(args.out), manifest)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
