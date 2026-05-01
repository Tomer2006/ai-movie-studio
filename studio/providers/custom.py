from __future__ import annotations

import subprocess
import tempfile
import textwrap
import os
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


def _drawtext_font_option() -> str:
    candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            return f"fontfile='{_drawtext_path(path)}':"
    return ""


def _prompt_document(prompt: str, negative_prompt: str | None) -> str:
    """Positive + optional negative exactly as passed into the provider (no UI labels)."""
    p = prompt.strip()
    n = (negative_prompt or "").strip()
    if not n:
        return p
    return f"{p}\n\n{n}"


def _wrap_width(frame_width: int, fontsize: int) -> int:
    # drawtext has no automatic wrapping; estimate a safe line length for the frame.
    average_char_width = max(1, int(fontsize * 0.55))
    usable_width = int(frame_width * 0.84)
    return max(24, min(90, usable_width // average_char_width))


def _wrapped_overlay(document: str, frame_width: int, fontsize: int) -> str:
    return textwrap.fill(
        document,
        width=_wrap_width(frame_width, fontsize),
        break_long_words=False,
        break_on_hyphens=False,
    )


def _overlay_fontsize(document: str, frame_height: int) -> int:
    length = len(document)
    base = max(30, min(46, int(frame_height * 0.058)))
    if length > 12000:
        return max(16, int(base * 0.45))
    if length > 8000:
        return max(18, int(base * 0.5))
    if length > 5000:
        return max(20, int(base * 0.58))
    if length > 3000:
        return max(24, int(base * 0.68))
    if length > 1500:
        return max(28, int(base * 0.8))
    return base


def _prompt_overlay(document: str, frame_width: int, frame_height: int) -> tuple[str, int, int]:
    fontsize = _overlay_fontsize(document, frame_height)
    while fontsize > 16:
        wrapped = _wrapped_overlay(document, frame_width, fontsize)
        line_spacing = max(5, int(fontsize * 0.35))
        line_count = max(1, wrapped.count("\n") + 1)
        approx_text_height = line_count * (fontsize + line_spacing) + 64
        if approx_text_height <= int(frame_height * 0.86):
            return wrapped, fontsize, line_spacing
        fontsize -= 2
    wrapped = _wrapped_overlay(document, frame_width, fontsize)
    return wrapped, fontsize, max(5, int(fontsize * 0.35))


class CustomVideoProvider(VideoProvider):
    """Local custom preview clip via ffmpeg testsrc (no generative video API).

    Use this to exercise prompts, timing, and assembly without API spend.
    For generated footage set ``VIDEO_PROVIDER`` to ``openrouter``, ``fal``,
    ``replicate``, ``xai``, or ``http`` (JSON HTTP driver).
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
        overlay_body, fontsize, line_spacing = _prompt_overlay(document, w, h)

        # Draw the prompt last so it stays above the preview label and test pattern.
        vf_base = f"testsrc2=size={w}x{h}:rate={fps}"
        font_option = _drawtext_font_option()

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
                f"drawtext={font_option}text='Custom (local preview)':fontcolor=white:"
                "fontsize=14:"
                "x=w-text_w-12:y=h-th-10:box=1:boxcolor=black@0.55:boxborderw=4,"
                f"drawtext={font_option}textfile='{_drawtext_path(overlay_path)}':"
                f"fontcolor=white:fontsize={fontsize}:"
                "x='(w-text_w)/2':y='(h-text_h)/2':"
                f"line_spacing={line_spacing}:box=1:boxcolor=black@0.82:"
                "boxborderw=14:shadowcolor=black@0.9:shadowx=2:shadowy=2"
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
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            output_path.with_suffix(".prompt.txt").write_text(document, encoding="utf-8")
        finally:
            if overlay_path is not None:
                overlay_path.unlink(missing_ok=True)
        return output_path
