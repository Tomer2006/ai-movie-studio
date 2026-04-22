from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx

from studio.providers.base import VideoProvider

_QUEUE_BASE = "https://queue.fal.run"


def _mp4_url_from_value(obj: Any) -> str | None:
    if isinstance(obj, str) and obj.startswith("http") and (".mp4" in obj or "/files/" in obj):
        if re.search(r"\.(mp4|webm|mov)(?:\?|$)", obj, re.I) or "fal.media" in obj:
            return obj
    if isinstance(obj, dict):
        u = obj.get("url")
        if isinstance(u, str) and (".mp4" in u or "/files/" in u):
            return u
        for v in obj.values():
            found = _mp4_url_from_value(v)
            if found:
                return found
    if isinstance(obj, list):
        for v in obj:
            found = _mp4_url_from_value(v)
            if found:
                return found
    return None


def _extract_video_url(data: object) -> str:
    if isinstance(data, dict) and "error" in data and data.get("error") is not None:
        err = data.get("error")
        et = data.get("error_type", "")
        raise RuntimeError(f"fal result error: {et}: {err!r}")
    if not isinstance(data, dict):
        raise RuntimeError(f"fal result is not an object: {data!r}")
    inner: Any = data
    for key in ("data", "output", "result"):
        w = data.get(key)
        if isinstance(w, dict):
            inner = w
    url = _mp4_url_from_value(inner) or _mp4_url_from_value(data)
    if not url:
        raise RuntimeError(f"No video URL in fal response: {data!r}")
    return str(url)


class FalVideoProvider(VideoProvider):
    """
    fal.ai Model API (queue) — set FAL_KEY and FAL_VIDEO_MODEL.
    See https://fal.ai/models for endpoint IDs; default is MiniMax Hailuo T2V.
    """

    def __init__(self) -> None:
        self.key = (os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY", "")).strip()
        if not self.key:
            raise RuntimeError(
                "FAL_KEY (or FAL_API_KEY) is required when VIDEO_PROVIDER=fal"
            )
        self.model = os.environ.get(
            "FAL_VIDEO_MODEL", "fal-ai/minimax/hailuo-02/standard/text-to-video"
        ).strip()
        self.max_wait_sec = int(os.environ.get("FAL_MAX_WAIT_SEC", "900"))
        self.poll_interval = float(os.environ.get("FAL_POLL_INTERVAL", "3"))

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Key {self.key}",
            "Content-Type": "application/json",
        }

    def _queue_url(self) -> str:
        # model id is a path, e.g. fal-ai/flux/schnell
        m = self.model.strip("/")
        return f"{_QUEUE_BASE}/{m}"

    def _build_body(
        self,
        prompt: str,
        duration_sec: float,
        negative_prompt: str | None,
        aspect_ratio: str,
        seed: int | None,
        reference_image_url: str | None,
    ) -> dict[str, Any]:
        _ = aspect_ratio
        _ = reference_image_url
        text = prompt
        if negative_prompt:
            text = f"{prompt} Avoid: {negative_prompt}"
        body: dict[str, Any] = {"prompt": text}
        extra_raw = os.environ.get("FAL_EXTRA_INPUT", "").strip()
        if extra_raw:
            merged = json.loads(extra_raw)
            if not isinstance(merged, dict):
                raise ValueError("FAL_EXTRA_INPUT must be a JSON object")
            body.update(merged)
        if "duration" not in body:
            low = self.model.lower()
            if "hailuo" in low and "text-to-video" in low:
                d = int(round(max(1.0, duration_sec)))
                body["duration"] = "6" if d <= 7 else "10"
                body.setdefault("prompt_optimizer", True)
            else:
                body["duration"] = max(1, min(120, int(round(duration_sec))))
        if seed is not None and "seed" not in body:
            body["seed"] = seed
        return {k: v for k, v in body.items() if v is not None}

    def _submit(self, client: httpx.Client, body: dict[str, Any]) -> dict[str, Any]:
        r = client.post(self._queue_url(), headers=self._headers(), json=body, timeout=60.0)
        if r.status_code >= 400:
            raise RuntimeError(f"fal submit failed HTTP {r.status_code}: {r.text[:2000]!r}")
        data = r.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"fal submit response is not an object: {data!r}")
        return data

    def _poll(
        self,
        client: httpx.Client,
        status_url: str,
    ) -> tuple[dict[str, Any], str | None]:
        deadline = time.monotonic() + self.max_wait_sec
        last_response_url: str | None = None
        while time.monotonic() < deadline:
            r = client.get(status_url, headers=self._headers(), timeout=60.0)
            r.raise_for_status()
            st = r.json()
            if not isinstance(st, dict):
                raise RuntimeError(f"fal status is not an object: {st!r}")
            last = st.get("response_url")
            if isinstance(last, str) and last.strip():
                last_response_url = last
            s = st.get("status", "")
            if s == "COMPLETED":
                if st.get("error") is not None or st.get("error_type") is not None:
                    err = st.get("error", st)
                    raise RuntimeError(f"fal job failed: {err!r}")
                return st, last_response_url
            if s in ("FAILED", "ERROR", "CANCELED", "CANCELLED"):
                raise RuntimeError(f"fal job terminal status {s!r}: {st!r}")
            time.sleep(self.poll_interval)
        raise TimeoutError("fal queue request timed out")

    def _fetch_result(
        self,
        client: httpx.Client,
        request_id: str,
        response_url: str | None,
    ) -> dict[str, Any]:
        url = response_url
        if not url:
            url = f"{self._queue_url()}/requests/{request_id}"
        r = client.get(url, headers=self._headers(), timeout=120.0)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"fal result is not an object: {data!r}")
        return data

    def _download(self, client: httpx.Client, video_url: str, dest: Path) -> None:
        r = client.get(video_url, follow_redirects=True, timeout=120.0)
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
        _ = fps
        body = self._build_body(
            prompt,
            duration_sec,
            negative_prompt,
            aspect_ratio,
            seed,
            reference_image_url,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        last_err: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client() as client:
                    start = self._submit(client, body)
                    request_id = start.get("request_id")
                    if not isinstance(request_id, str) or not request_id:
                        raise RuntimeError(f"No request_id in fal response: {start!r}")
                    status_url = start.get("status_url")
                    if not isinstance(status_url, str) or not status_url:
                        raise RuntimeError(f"No status_url in fal response: {start!r}")
                    resp_url = start.get("response_url")
                    if isinstance(resp_url, str) and resp_url:
                        pre = resp_url
                    else:
                        pre = None
                    completed, ru = self._poll(client, status_url)
                    final_ru: str | None = ru or (pre if isinstance(pre, str) else None)
                    if final_ru is None:
                        final_ru = completed.get("response_url")
                        if not isinstance(final_ru, str):
                            final_ru = None
                    data = self._fetch_result(client, request_id, final_ru)
                    vurl = _extract_video_url(data)
                    self._download(client, vurl, output_path)
                    return output_path
            except (httpx.HTTPError, RuntimeError, TimeoutError, OSError, ValueError) as e:
                last_err = e
                time.sleep(2**attempt)

        assert last_err is not None
        raise last_err
