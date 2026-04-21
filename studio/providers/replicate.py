from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from studio.providers.base import VideoProvider


class ReplicateVideoProvider(VideoProvider):
    """Replicate HTTP API — model from REPLICATE_VIDEO_MODEL (owner/name)."""

    def __init__(self) -> None:
        self.token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
        if not self.token:
            raise RuntimeError("REPLICATE_API_TOKEN is required when VIDEO_PROVIDER=replicate")
        self.model = os.environ.get("REPLICATE_VIDEO_MODEL", "minimax/video-01").strip()
        self.max_poll_sec = int(os.environ.get("REPLICATE_MAX_WAIT_SEC", "600"))
        self.poll_interval = float(os.environ.get("REPLICATE_POLL_INTERVAL", "2"))

    def _predict_url(self) -> str:
        if "/" not in self.model:
            raise ValueError(
                "REPLICATE_VIDEO_MODEL must be owner/name, e.g. minimax/video-01"
            )
        return f"https://api.replicate.com/v1/models/{self.model}/predictions"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _build_input(
        self,
        prompt: str,
        duration_sec: float,
        negative_prompt: str | None,
        aspect_ratio: str,
        fps: int,
        seed: int | None,
        reference_image_url: str | None,
    ) -> dict[str, Any]:
        """Minimal portable input; merge REPLICATE_EXTRA_INPUT JSON for model-specific keys."""
        inp: dict[str, Any] = {"prompt": prompt}
        if negative_prompt:
            inp["negative_prompt"] = negative_prompt
        if seed is not None:
            inp["seed"] = seed
        extra_raw = os.environ.get("REPLICATE_EXTRA_INPUT", "").strip()
        if extra_raw:
            merged = json.loads(extra_raw)
            if not isinstance(merged, dict):
                raise ValueError("REPLICATE_EXTRA_INPUT must be a JSON object")
            inp.update(merged)
        return inp

    def _poll(self, client: httpx.Client, get_url: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.max_poll_sec
        while time.monotonic() < deadline:
            r = client.get(get_url, headers=self._headers())
            r.raise_for_status()
            body = r.json()
            status = body.get("status")
            if status == "succeeded":
                return body
            if status in ("failed", "canceled"):
                raise RuntimeError(f"Replicate job {status}: {body!r}")
            time.sleep(self.poll_interval)
        raise TimeoutError("Replicate prediction timed out")

    def _download_video(self, url: str, dest: Path) -> None:
        with httpx.Client(timeout=120.0) as client:
            r = client.get(url, follow_redirects=True)
            r.raise_for_status()
            dest.write_bytes(r.content)

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
        inp = self._build_input(
            prompt, duration_sec, negative_prompt, aspect_ratio, fps, seed, reference_image_url
        )
        # Remove None values for cleaner POST
        inp = {k: v for k, v in inp.items() if v is not None}

        last_err: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=60.0) as client:
                    r = client.post(
                        self._predict_url(),
                        headers=self._headers(),
                        json={"input": inp},
                    )
                    if r.status_code >= 400:
                        last_err = RuntimeError(r.text)
                        time.sleep(2**attempt)
                        continue
                    r.raise_for_status()
                    pred = r.json()
                    get_url = pred["urls"]["get"]
                    done = self._poll(client, get_url)
                    out = done.get("output")
                    if not out:
                        raise RuntimeError(f"No output in prediction: {done!r}")
                    if isinstance(out, list):
                        url = out[0]
                    else:
                        url = str(out)
                    self._download_video(url, output_path)
                    return output_path
            except (httpx.HTTPError, TimeoutError, RuntimeError) as e:
                last_err = e
                time.sleep(2**attempt)
        assert last_err is not None
        raise last_err
