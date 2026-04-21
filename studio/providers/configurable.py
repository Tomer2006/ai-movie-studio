from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
import jsonschema

from studio.paths import repo_root, schema_path
from studio.providers.base import VideoProvider

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env(s: str) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        v = os.environ.get(key, "")
        return v

    return _ENV_PATTERN.sub(repl, s)


def _get_path(data: Any, path: list[str]) -> Any:
    cur: Any = data
    for key in path:
        if isinstance(cur, dict):
            if key not in cur:
                raise KeyError(f"Missing key {key!r} in path {path!r}")
            cur = cur[key]
        else:
            raise TypeError(f"Cannot traverse {type(cur).__name__} at {key!r}")
    return cur


def _format_recursive(obj: Any, ctx: dict[str, str]) -> Any:
    if isinstance(obj, str):
        s = _expand_env(obj)
        return s.format(**ctx)
    if isinstance(obj, dict):
        return {k: _format_recursive(v, ctx) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_format_recursive(v, ctx) for v in obj]
    return obj


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    with open(schema_path("http_provider.schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    jsonschema.validate(instance=data, schema=schema)
    return data


def _ctx_for_shot(
    *,
    prompt: str,
    duration_sec: float,
    negative_prompt: str | None,
    aspect_ratio: str,
    seed: int | None,
    reference_image_url: str | None,
) -> dict[str, str]:
    dur_int = max(1, min(120, int(round(duration_sec))))
    return {
        "prompt": prompt,
        "duration_sec": str(duration_sec),
        "duration_int": str(dur_int),
        "aspect_ratio": aspect_ratio,
        "negative_prompt": negative_prompt or "",
        "reference_image_url": reference_image_url or "",
        "seed": "" if seed is None else str(seed),
    }


class ConfigurableHttpProvider(VideoProvider):
    """Video provider driven by JSON (HTTP start + optional poll + download)."""

    def __init__(self, config: dict[str, Any], *, source: str | None = None) -> None:
        self.cfg = config
        self.source = source or "config"

    @classmethod
    def from_file(cls, path: Path | str) -> ConfigurableHttpProvider:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"Provider config not found: {p}")
        cfg = _load_and_validate_config(p)
        cls._check_logical_constraints(cfg)
        return cls(cfg, source=str(p))

    @staticmethod
    def _check_logical_constraints(cfg: dict[str, Any]) -> None:
        job = cfg["job"]
        mode = job["mode"]
        if mode == "poll":
            if "request_id" not in job:
                raise ValueError("job.request_id is required when job.mode is poll")
            if "poll" not in job:
                raise ValueError("job.poll is required when job.mode is poll")
            if "status" not in job:
                raise ValueError("job.status is required when job.mode is poll")
            if "video_url" not in job:
                raise ValueError("job.video_url is required when job.mode is poll")
        else:
            if "video_url" not in job:
                raise ValueError("job.video_url is required when job.mode is immediate")

    def _merge_headers(self, h: dict[str, str] | None) -> dict[str, str]:
        out: dict[str, str] = {}
        for k, v in (h or {}).items():
            out[k] = _expand_env(v)
        return out

    def _start(
        self, client: httpx.Client, ctx: dict[str, str]
    ) -> tuple[int, dict[str, Any]]:
        st = self.cfg["start"]
        url = _format_recursive(st["url"], ctx)
        method = (st.get("method") or "POST").upper()
        headers = self._merge_headers(st.get("headers"))
        body: Any = None
        if "body" in st:
            body = _format_recursive(st["body"], ctx)
        r = client.request(method, url, headers=headers, json=body if body is not None else None)
        try:
            data = r.json()
        except Exception as e:
            raise RuntimeError(
                f"Start response is not JSON (HTTP {r.status_code}): {r.text[:800]!r}"
            ) from e
        if not isinstance(data, dict):
            raise RuntimeError(f"Start JSON must be an object, got: {type(data).__name__}")
        return r.status_code, data

    def _poll_loop(
        self,
        client: httpx.Client,
        *,
        request_id: str,
        ctx: dict[str, str],
    ) -> dict[str, Any]:
        job = self.cfg["job"]
        poll = job["poll"]
        assert poll is not None
        status_cfg = job["status"]
        video_cfg = job["video_url"]

        url = _format_recursive(poll["url_template"], {**ctx, "request_id": request_id})
        method = (poll.get("method") or "GET").upper()
        poll_headers = self._merge_headers(poll.get("headers"))
        poll_body = poll.get("body")
        if poll_body is not None:
            poll_body = _format_recursive(poll_body, {**ctx, "request_id": request_id})

        interval = float(poll.get("interval_sec") or 5)
        max_sec = float(poll.get("max_sec") or 900)
        done_vals = set(status_cfg["done_values"])
        failed_vals = set(
            status_cfg.get("failed_values") or ["failed", "error", "canceled", "expired"]
        )

        deadline = time.monotonic() + max_sec
        while time.monotonic() < deadline:
            r = client.request(
                method,
                url,
                headers=poll_headers,
                json=poll_body if poll_body is not None else None,
            )
            r.raise_for_status()
            pdata = r.json()
            if not isinstance(pdata, dict):
                raise RuntimeError(f"Poll response is not a JSON object: {pdata!r}")
            try:
                st = _get_path(pdata, status_cfg["path"])
            except (KeyError, TypeError) as e:
                raise RuntimeError(f"Status path invalid: {e!r}; body={pdata!r}") from e
            st_str = str(st)
            if st_str in done_vals:
                return pdata
            if st_str in failed_vals:
                raise RuntimeError(f"Provider reported failure status={st_str!r}: {pdata!r}")
            time.sleep(interval)
        raise TimeoutError("Configurable provider poll timed out")

    def _download(
        self,
        client: httpx.Client,
        url: str,
        dest: Path,
    ) -> None:
        dl = self.cfg.get("download") or {}
        method = (dl.get("method") or "GET").upper()
        headers = self._merge_headers(dl.get("headers"))
        r = client.request(method, url, headers=headers)
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
        ctx = _ctx_for_shot(
            prompt=prompt,
            duration_sec=duration_sec,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            seed=seed,
            reference_image_url=reference_image_url,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        job = self.cfg["job"]
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=120.0) as client:
                    status, start_data = self._start(client, ctx)
                    if status >= 400:
                        raise RuntimeError(f"Start request failed HTTP {status}: {start_data!r}")

                    if job["mode"] == "immediate":
                        vurl = _get_path(start_data, job["video_url"]["path"])
                        if not isinstance(vurl, str):
                            raise RuntimeError(f"video_url is not a string: {vurl!r}")
                        vurl = _expand_env(vurl)
                        self._download(client, vurl, output_path)
                        return output_path

                    rid = _get_path(start_data, job["request_id"]["path"])
                    rid_str = str(rid)
                    polled = self._poll_loop(client, request_id=rid_str, ctx=ctx)
                    vurl = _get_path(polled, job["video_url"]["path"])
                    if not isinstance(vurl, str):
                        raise RuntimeError(f"video_url is not a string: {vurl!r}")
                    vurl = _expand_env(vurl)
                    self._download(client, vurl, output_path)
                    return output_path
            except (httpx.HTTPError, TimeoutError, RuntimeError, OSError, KeyError, TypeError) as e:
                last_err = e
                time.sleep(2**attempt)
        assert last_err is not None
        raise last_err


def load_configurable_provider() -> ConfigurableHttpProvider:
    """Load provider from STUDIO_PROVIDER_CONFIG (relative to repo root)."""
    rel = os.environ.get("STUDIO_PROVIDER_CONFIG", "").strip()
    if not rel:
        raise RuntimeError(
            "Set STUDIO_PROVIDER_CONFIG to a JSON file path (e.g. providers/my.json) "
            "when using VIDEO_PROVIDER=custom."
        )
    path = repo_root() / rel
    return ConfigurableHttpProvider.from_file(path)
