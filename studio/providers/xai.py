from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import httpx

from studio.providers.base import VideoProvider


class XaiVideoProvider(VideoProvider):
    """xAI Grok Imagine video API — https://docs.x.ai/docs/guides/video-generation"""

    BASE = "https://api.x.ai/v1"

    def __init__(self) -> None:
        self.api_key = os.environ.get("XAI_API_KEY", "").strip()
        if not self.api_key:
            raise RuntimeError("XAI_API_KEY is required when VIDEO_PROVIDER=xai")
        self.model = os.environ.get("XAI_VIDEO_MODEL", "grok-imagine-video").strip()
        self.resolution = os.environ.get("XAI_VIDEO_RESOLUTION", "720p").strip()
        self.max_poll_sec = int(os.environ.get("XAI_MAX_WAIT_SEC", "900"))
        self.poll_interval = float(os.environ.get("XAI_POLL_INTERVAL", "5"))

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_body(
        self,
        prompt: str,
        duration_sec: float,
        negative_prompt: str | None,
        aspect_ratio: str,
        reference_image_url: str | None,
    ) -> dict[str, Any]:
        dur = int(round(duration_sec))
        dur = max(1, min(15, dur))
        text = prompt
        if negative_prompt:
            text = f"{prompt}. Avoid: {negative_prompt}"
        body: dict[str, Any] = {
            "model": self.model,
            "prompt": text,
            "duration": dur,
            "aspect_ratio": aspect_ratio,
            "resolution": self.resolution,
        }
        if reference_image_url:
            body["reference_images"] = [{"url": reference_image_url}]
        return body

    def _poll(self, client: httpx.Client, request_id: str) -> dict[str, Any]:
        url = f"{self.BASE}/videos/{request_id}"
        deadline = time.monotonic() + self.max_poll_sec
        while time.monotonic() < deadline:
            r = client.get(url, headers=self._headers())
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            if status == "done":
                return data
            if status == "failed":
                err = data.get("error") or data
                raise RuntimeError(f"xAI video failed: {err!r}")
            if status == "expired":
                raise RuntimeError("xAI video request expired")
            time.sleep(self.poll_interval)
        raise TimeoutError("xAI video generation timed out")

    def _download(self, url: str, dest: Path) -> None:
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            r = client.get(url)
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
        _ = fps  # xAI controls output; fps from bible unused
        _ = seed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        body = self._build_body(
            prompt, duration_sec, negative_prompt, aspect_ratio, reference_image_url
        )
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=120.0) as client:
                    r = client.post(
                        f"{self.BASE}/videos/generations",
                        headers=self._headers(),
                        json=body,
                    )
                    if r.status_code >= 400:
                        last_err = RuntimeError(r.text)
                        time.sleep(2**attempt)
                        continue
                    r.raise_for_status()
                    request_id = r.json().get("request_id")
                    if not request_id:
                        raise RuntimeError(f"No request_id in response: {r.text!r}")
                    done = self._poll(client, request_id)
                    v = done.get("video") or {}
                    url = v.get("url")
                    if not url:
                        raise RuntimeError(f"No video URL in result: {done!r}")
                    self._download(url, output_path)
                    return output_path
            except (httpx.HTTPError, TimeoutError, RuntimeError, OSError) as e:
                last_err = e
                time.sleep(2**attempt)
        assert last_err is not None
        raise last_err
