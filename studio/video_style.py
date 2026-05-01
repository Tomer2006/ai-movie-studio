from __future__ import annotations

from typing import Any

_VIDEO_STYLE_FIELDS: tuple[tuple[str, str], ...] = (
    ("Whole-film aesthetic", "aesthetic"),
    ("Look", "look"),
    ("Camera language", "camera_language"),
    ("Lighting", "lighting"),
    ("Texture / film", "texture_and_film"),
    ("Color grading", "color_grading"),
    ("Motion / pacing", "motion_and_pacing"),
    ("Consistency lock", "consistency_notes"),
)


def build_video_style_block(bible_doc: dict[str, Any]) -> str:
    """Locked global video look; appended to every render prompt when present."""
    raw = bible_doc.get("video_style")
    if not isinstance(raw, dict):
        return ""
    lines: list[str] = []
    for label, key in _VIDEO_STYLE_FIELDS:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            lines.append(f"- {label}: {value.strip()}")
    if not lines:
        return ""
    return "\n".join(
        [
            "Global video style (entire movie — every shot and clip):",
            "Same rendering intent for the full runtime, not a one-off look. "
            "Apply consistently unless this shot prompt explicitly overrides a named element.",
        ]
        + lines
    )


def video_style_negative_prompt(bible_doc: dict[str, Any]) -> str | None:
    """Return bible `video_style.negative_prompt` when set."""
    vs = bible_doc.get("video_style")
    if isinstance(vs, dict):
        vn = vs.get("negative_prompt")
        if isinstance(vn, str) and vn.strip():
            return vn.strip()
    return None
