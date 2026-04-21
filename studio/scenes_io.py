from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ShotRef:
    scene_id: str
    shot_id: str
    duration_sec: float
    prompt: str
    negative_prompt: str | None
    seed: int | None
    reference_image_url: str | None


def iter_shots(scenes_doc: dict[str, Any]) -> list[ShotRef]:
    out: list[ShotRef] = []
    for scene in scenes_doc["scenes"]:
        sid = scene["id"]
        for shot in scene["shots"]:
            out.append(
                ShotRef(
                    scene_id=sid,
                    shot_id=shot["id"],
                    duration_sec=float(shot["duration_sec"]),
                    prompt=shot["prompt"],
                    negative_prompt=shot.get("negative_prompt"),
                    seed=shot.get("seed"),
                    reference_image_url=shot.get("reference_image_url"),
                )
            )
    return out


def clip_path(clips_dir: Path, scene_id: str, shot_id: str) -> Path:
    safe_scene = scene_id.replace("/", "_")
    safe_shot = shot_id.replace("/", "_")
    return clips_dir / f"{safe_scene}__{safe_shot}.mp4"


def full_narration_text(scenes_doc: dict[str, Any]) -> str:
    parts: list[str] = []
    for scene in scenes_doc["scenes"]:
        n = (scene.get("narration") or "").strip()
        if n:
            parts.append(n)
    return "\n\n".join(parts)
