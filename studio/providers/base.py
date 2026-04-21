from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class VideoProvider(ABC):
    """Generate a short video clip for one shot."""

    @abstractmethod
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
        """Write an MP4 to output_path and return the same path."""
        raise NotImplementedError
