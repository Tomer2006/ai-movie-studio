from __future__ import annotations

import subprocess
import tempfile
import textwrap
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


def _drawtext_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", "\\:")


def _prompt_document(prompt: str, negative_prompt: str | None) -> str:
    """Positive + optional negative exactly as passed into the provider (no UI labels)."""
    p = prompt.strip()
    n = (negative_prompt or "").strip()
    if not n:
        return p
    return f"{p}\n\n{n}"


def _wrapped_overlay(document: str) -> str:
    width = 110 if len(document) < 3500 else 130
    return textwrap.fill(
        document,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _overlay_fontsize(text: str) -> int:
    length = len(text)
    if length > 12000:
        return 12
    if length > 8000:
        return 14
    if length > 5000:
        return 16
    if length > 3000:
        return 18
    return 20


class MockVideoProvider(VideoProvider):
    """Generate a placeholder clip with ffmpeg testsrc (no cloud API).

    This is **not** AI video — it is colored test bars so you can test concat/assembly
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
        document = _prompt_document(prompt, negative_prompt)
        overlay_body = _wrapped_overlay(document)
        fontsize = _overlay_fontsize(overlay_body)

        # testsrc2 + centered static prompt (real pipeline text). Corner label only.
        vf_base = f"testsrc2=size={w}x{h}:rate={fps}"
        line_spacing = max(4, int(fontsize * 0.35))
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

        overlay_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".txt",
                delete=False,
                newline="\n",
            ) as tf:
                tf.write(overlay_body)
                overlay_path = Path(tf.name)

            vf_labeled = (
                f"{vf_base},"
                f"drawtext=textfile='{_drawtext_path(overlay_path)}':"
                f"fontcolor=white:fontsize={fontsize}:"
                "x='(w-text_w)/2':y='(h-text_h)/2':"
                f"line_spacing={line_spacing}:box=1:boxcolor=black@0.70:boxborderw=8,"
                "drawtext=text='Mock (not AI)':fontcolor=white:fontsize=14:"
                "x=w-text_w-12:y=h-th-10:box=1:boxcolor=black@0.55:boxborderw=4"
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
                subprocess.run(cmd_fallback, check=True, capture_output=True, text=True)
            output_path.with_suffix(".prompt.txt").write_text(document, encoding="utf-8")
        finally:
            if overlay_path is not None:
                overlay_path.unlink(missing_ok=True)
        return output_path
