from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from studio.scenes_io import clip_path, iter_shots


def _write_concat_list(paths: list[Path], list_file: Path) -> None:
    lines = []
    for p in paths:
        # ffmpeg concat demuxer: escape single quotes
        escaped = str(p.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def assemble(
    *,
    scenes_doc: dict[str, Any],
    clips_dir: Path,
    output_mp4: Path,
) -> Path:
    """Concatenate rendered clips in scene order; preserves each clip's video and embedded audio."""
    shots = iter_shots(scenes_doc)
    ordered: list[Path] = []
    missing: list[str] = []
    for s in shots:
        p = clip_path(clips_dir, s.scene_id, s.shot_id)
        if not p.is_file():
            missing.append(str(p))
        ordered.append(p)
    if missing:
        raise FileNotFoundError("Missing clip files:\n" + "\n".join(missing))

    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        concat_list = tmp_path / "concat.txt"
        _write_concat_list(ordered, concat_list)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(output_mp4),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    return output_mp4
