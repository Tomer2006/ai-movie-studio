from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from studio.scenes_io import clip_path, full_narration_text, iter_shots
from studio.tts import synthesize_narration, tts_provider_name


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
    """Concatenate clips in scene order; mux narration if configured."""
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
        video_only = tmp_path / "video_only.mp4"
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
                str(video_only),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        narr = full_narration_text(scenes_doc)
        audio_path = tmp_path / "narration.mp3"
        audio = synthesize_narration(narr, audio_path)

        if audio and audio.is_file() and tts_provider_name() != "none":
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(video_only),
                    "-i",
                    str(audio),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(output_mp4),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            shutil.copy2(video_only, output_mp4)

    return output_mp4
