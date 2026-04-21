from __future__ import annotations

import math
import subprocess
from pathlib import Path


def review_sheet_path(review_dir: Path, scene_id: str, shot_id: str, attempt: int) -> Path:
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    safe_scene = scene_id.replace("/", "_")
    safe_shot = shot_id.replace("/", "_")
    return review_dir / safe_scene / safe_shot / f"attempt_{attempt:02d}.png"


def render_review_sheet(
    *,
    clip_path: Path,
    output_path: Path,
    duration_sec: float,
    sample_count: int = 6,
    columns: int = 3,
    cell_size: int = 320,
) -> Path:
    """Build a single PNG contact sheet from a rendered clip using ffmpeg."""
    if not clip_path.is_file():
        raise FileNotFoundError(f"Clip not found: {clip_path}")
    if duration_sec <= 0:
        raise ValueError("duration_sec must be > 0")
    if sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    if columns < 1:
        raise ValueError("columns must be >= 1")
    if cell_size < 64:
        raise ValueError("cell_size must be >= 64")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    columns = min(columns, sample_count)
    rows = max(1, math.ceil(sample_count / columns))
    fps_value = sample_count / max(duration_sec, 1.0)

    # Preserve the clip aspect ratio and pad into fixed cells so all frames tile cleanly.
    vf = (
        f"fps={fps_value:.6f},"
        f"scale={cell_size}:{cell_size}:force_original_aspect_ratio=decrease,"
        f"pad={cell_size}:{cell_size}:(ow-iw)/2:(oh-ih)/2:black,"
        f"tile={columns}x{rows}"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(clip_path),
        "-vf",
        vf,
        "-frames:v",
        "1",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path
