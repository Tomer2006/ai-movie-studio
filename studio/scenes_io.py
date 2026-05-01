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


def _make_shot_ref(scene_id: str, shot: dict[str, Any]) -> ShotRef:
    return ShotRef(
        scene_id=scene_id,
        shot_id=shot["id"],
        duration_sec=float(shot["duration_sec"]),
        prompt=shot["prompt"],
        negative_prompt=shot.get("negative_prompt"),
        seed=shot.get("seed"),
        reference_image_url=shot.get("reference_image_url"),
    )


def iter_shots(scenes_doc: dict[str, Any]) -> list[ShotRef]:
    out: list[ShotRef] = []
    for scene in scenes_doc["scenes"]:
        sid = scene["id"]
        for shot in scene["shots"]:
            out.append(_make_shot_ref(sid, shot))
    return out


def find_shot(scenes_doc: dict[str, Any], scene_id: str, shot_id: str) -> ShotRef | None:
    for scene in scenes_doc["scenes"]:
        if scene["id"] != scene_id:
            continue
        for shot in scene["shots"]:
            if shot["id"] == shot_id:
                return _make_shot_ref(scene_id, shot)
    return None


def clip_path(clips_dir: Path, scene_id: str, shot_id: str) -> Path:
    safe_scene = scene_id.replace("/", "_")
    safe_shot = shot_id.replace("/", "_")
    return clips_dir / f"{safe_scene}__{safe_shot}.mp4"


def prompt_path(clips_dir: Path, scene_id: str, shot_id: str) -> Path:
    return clip_path(clips_dir, scene_id, shot_id).with_suffix(".prompt.txt")
