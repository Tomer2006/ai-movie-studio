from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from studio.paths import repo_root, schema_path


def _schema(schema_file: str) -> dict[str, Any]:
    with open(schema_path(schema_file), encoding="utf-8") as f:
        return json.load(f)


def validate_continuity_bible(data: dict[str, Any]) -> None:
    jsonschema.validate(instance=data, schema=_schema("continuity_bible.schema.json"))


def validate_scenes(data: dict[str, Any]) -> None:
    jsonschema.validate(instance=data, schema=_schema("scenes.schema.json"))


def load_and_validate_bible(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    validate_continuity_bible(data)
    return data


def load_and_validate_scenes(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    validate_scenes(data)
    return data


def default_paths() -> tuple[Path, Path]:
    root = repo_root()
    return root / "continuity_bible.json", root / "scenes.json"
