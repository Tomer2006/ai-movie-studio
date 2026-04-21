from __future__ import annotations

import subprocess
from pathlib import Path

from studio.providers.base import VideoProvider


def _ratio_to_size(aspect_ratio: str) -> tuple[int, int]:
    mapping = {
        "16:9": (1280, 720),
        "9:16": (720, 1280),
        "1:1": (720, 720),
        "4:3": (960, 720),
        "21:9": (1280, 548),
    }
    return mapping.get(aspect_ratio, (1280, 720))


class MockVideoProvider(VideoProvider):
    """Generate a placeholder clip with ffmpeg testsrc (no cloud API).

    This is **not** AI video — it is colored test bars so you can test concat/TTS
    without spending API credits. Real video requires VIDEO_PROVIDER=xai|replicate|custom.
    """

    def render_shot(
        self,
        *,
        output_path: Path,
        prompt: str,
        duration_sec: float,
        negative_prompt: str | None,
        aspect_ratio: str,
        fps: int,
        seed: int | None,
        reference_image_url: str | None,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        w, h = _ratio_to_size(aspect_ratio)
        # testsrc2 + burn-in so output is never mistaken for a failed AI render
        vf_base = f"testsrc2=size={w}x{h}:rate={fps}"
        vf_labeled = (
            f"{vf_base},drawtext=text='MOCK PLACEHOLDER - Not AI video':"
            "fontcolor=white:fontsize=28:x=24:y=24:"
            "box=1:boxcolor=black@0.65:boxborderw=8"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            vf_labeled,
            "-t",
            str(duration_sec),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError:
            cmd_fallback = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                vf_base,
                "-t",
                str(duration_sec),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(output_path),
            ]
            subprocess.run(cmd_fallback, check=True, capture_output=True, text=True)
        return output_path
