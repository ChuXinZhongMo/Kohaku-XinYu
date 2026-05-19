from __future__ import annotations

import re
from typing import Any


DATED_MATERIAL_ID_PATTERN = r"material-\d{4}-\d{2}-\d{2}-\d{3}"
ANY_MATERIAL_ID_PATTERN = r"material-[\w-]+"


def split_material_sections(
    text: str,
    *,
    allow_named_ids: bool = False,
    rstrip_body: bool = False,
) -> tuple[str, list[dict[str, Any]]]:
    id_pattern = ANY_MATERIAL_ID_PATTERN if allow_named_ids else DATED_MATERIAL_ID_PATTERN
    parts = re.split(rf"(?m)^## ({id_pattern})\n", text)
    preface = parts[0].rstrip()
    sections: list[dict[str, Any]] = []
    if len(parts) < 3:
        return preface, sections
    for index in range(1, len(parts), 2):
        material_id = parts[index].strip()
        body = parts[index + 1].rstrip() if rstrip_body else parts[index + 1]
        sections.append(
            {
                "material_id": material_id,
                "body": body,
                "fields": extract_dash_fields(body),
            }
        )
    return preface, sections


def extract_dash_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ": " not in stripped:
            continue
        key, value = stripped[2:].split(": ", 1)
        fields[key.strip()] = value.strip()
    return fields


def material_field_map(
    section: dict[str, Any],
    *,
    fields: tuple[str, ...],
    defaults: dict[str, str],
) -> dict[str, str]:
    extracted = section.get("fields") if isinstance(section.get("fields"), dict) else {}
    item = {"material_id": str(section.get("material_id", "")).strip()}
    for field in fields:
        value = extracted.get(field, defaults.get(field, "unknown"))
        item[field] = str(value).strip()
    return item


def split_material_field_maps(
    text: str,
    *,
    fields: tuple[str, ...],
    defaults: dict[str, str],
    allow_named_ids: bool = False,
) -> list[dict[str, str]]:
    _, sections = split_material_sections(text, allow_named_ids=allow_named_ids)
    return [material_field_map(section, fields=fields, defaults=defaults) for section in sections]


def integrated_source_material_ids(text: str) -> set[str]:
    return set(re.findall(rf"(?m)^- source_material:\s*({DATED_MATERIAL_ID_PATTERN})\s*$", text))
