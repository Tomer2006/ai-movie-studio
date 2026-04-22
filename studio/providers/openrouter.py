from __future__ import annotations

import os
import time
from pathlib import Path

import httpx

from studio.providers.base import VideoProvider


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default

    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be one of: true/false, 1/0, yes/no, on/off")


class OpenRouterVideoProvider(VideoProvider):
    """OpenRouter video generation API."""

    BASE = "https://openrouter.ai/api/v1"

    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is required when VIDEO_PROVIDER=openrouter"
            )

        self.model = os.environ.get("OPENROUTER_VIDEO_MODEL", "google/veo-3.1").strip()
        self.resolution = os.environ.get("OPENROUTER_VIDEO_RESOLUTION", "720p").strip()
        self.generate_audio = _env_bool("OPENROUTER_GENERATE_AUDIO", False)
        self.max_poll_sec = int(os.environ.get("OPENROUTER_MAX_WAIT_SEC", "900"))
        self.poll_interval = float(os.environ.get("OPENROUTER_POLL_INTERVAL", "5"))
        self.http_referer = os.environ.get("OPENROUTER_HTTP_REFERER", "").strip()
        self.title = os.environ.get("OPENROUTER_X_TITLE", "AI Movie Studio").strip()

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        if self.title:
            headers["X-Title"] = self.title
        return headers

    def _json_headers(self) -> dict[str, str]:
        return {
            **self._auth_headers(),
            "Content-Type": "application/json",
        }

    def _build_body(
        self,
        *,
        prompt: str,
        duration_sec: float,
        negative_prompt: str | None,
        aspect_ratio: str,
        seed: int | None,
    ) -> dict[str, object]:
        text = prompt
        # OpenRouter's video API does not currently expose a dedicated negative prompt field.
        if negative_prompt:
            text = f"{prompt}. Avoid: {negative_prompt}"

        body: dict[str, object] = {
            "model": self.model,
            "prompt": text,
            "aspect_ratio": aspect_ratio,
            "duration": max(1, int(round(duration_sec))),
            "resolution": self.resolution,
        }
        if seed is not None:
            body["seed"] = seed
        if self.generate_audio:
            body["generate_audio"] = True
        return body

    def _poll(self, client: httpx.Client, job_id: str) -> dict[str, object]:
        deadline = time.monotonic() + self.max_poll_sec
        url = f"{self.BASE}/videos/{job_id}"
        while time.monotonic() < deadline:
            response = client.get(url, headers=self._auth_headers())
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise RuntimeError(f"Unexpected OpenRouter poll response: {data!r}")

            status = str(data.get("status", "")).lower()
            if status == "completed":
                return data
            if status in {"failed", "cancelled", "expired"}:
                err = data.get("error") or data
                raise RuntimeError(f"OpenRouter video failed: {err!r}")

            time.sleep(self.poll_interval)

        raise TimeoutError("OpenRouter video generation timed out")

    def _download_content(self, client: httpx.Client, job_id: str, dest: Path) -> None:
        with client.stream(
            "GET",
            f"{self.BASE}/videos/{job_id}/content",
            headers=self._auth_headers(),
            params={"index": 0},
        ) as response:
            response.raise_for_status()
            with dest.open("wb") as fh:
                for chunk in response.iter_bytes():
                    fh.write(chunk)

    def _download_url(self, url: str, dest: Path) -> None:
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                with dest.open("wb") as fh:
                    for chunk in response.iter_bytes():
                        fh.write(chunk)

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
        _ = fps
        _ = reference_image_url

        output_path.parent.mkdir(parents=True, exist_ok=True)
        body = self._build_body(
            prompt=prompt,
            duration_sec=duration_sec,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            seed=seed,
        )

        last_err: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                    response = client.post(
                        f"{self.BASE}/videos",
                        headers=self._json_headers(),
                        json=body,
                    )
                    if response.status_code >= 400:
                        last_err = RuntimeError(response.text)
                        time.sleep(2**attempt)
                        continue

                    response.raise_for_status()
                    created = response.json()
                    if not isinstance(created, dict):
                        raise RuntimeError(
                            f"Unexpected OpenRouter create response: {created!r}"
                        )

                    job_id = created.get("id")
                    if not isinstance(job_id, str) or not job_id:
                        raise RuntimeError(f"No job id in response: {created!r}")

                    done = self._poll(client, job_id)
                    try:
                        self._download_content(client, job_id, output_path)
                    except httpx.HTTPError:
                        unsigned_urls = done.get("unsigned_urls")
                        if isinstance(unsigned_urls, list) and unsigned_urls:
                            self._download_url(str(unsigned_urls[0]), output_path)
                        else:
                            raise
                    return output_path
            except (httpx.HTTPError, RuntimeError, TimeoutError, OSError, ValueError) as exc:
                last_err = exc
                time.sleep(2**attempt)

        assert last_err is not None
        raise last_err
