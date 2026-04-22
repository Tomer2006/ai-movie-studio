from __future__ import annotations

import os
from pathlib import Path

from studio.paths import load_dotenv, repo_root
from studio.providers.base import VideoProvider
from studio.providers.configurable import ConfigurableHttpProvider, load_configurable_provider
from studio.providers.mock import MockVideoProvider
from studio.providers.openrouter import OpenRouterVideoProvider
from studio.providers.replicate import ReplicateVideoProvider
from studio.providers.xai import XaiVideoProvider

_BUILTIN = frozenset({"mock", "replicate", "xai", "openrouter", "custom"})


def _resolve_config_path(raw: str) -> Path | None:
    """Return path to JSON config if user passed a path-like VIDEO_PROVIDER."""
    root = repo_root()
    s = raw.strip()
    low = s.lower()
    if low.startswith("file:"):
        p = Path(s[5:].strip())
    elif low.startswith("config:"):
        p = Path(s[7:].strip())
    else:
        p = Path(s)
    if not p.is_absolute():
        p = root / p
    if p.is_file():
        return p
    return None


def configured_provider_raw() -> str:
    """Return the configured VIDEO_PROVIDER value after loading .env."""
    load_dotenv()
    return os.environ.get("VIDEO_PROVIDER", "mock").strip()


def describe_provider(provider: VideoProvider) -> str:
    """Return a short user-facing description of the resolved provider."""
    if isinstance(provider, MockVideoProvider):
        return "mock"
    if isinstance(provider, ReplicateVideoProvider):
        return f"replicate ({provider.model})"
    if isinstance(provider, XaiVideoProvider):
        return f"xai ({provider.model})"
    if isinstance(provider, OpenRouterVideoProvider):
        return f"openrouter ({provider.model})"
    if isinstance(provider, ConfigurableHttpProvider):
        return f"custom ({provider.source})"
    return type(provider).__name__


def get_provider() -> VideoProvider:
    """
    Resolve video provider from env.

    Built-ins: mock, replicate, xai, openrouter, custom

    - ``custom``: requires ``STUDIO_PROVIDER_CONFIG`` (path under repo root to JSON).
    - Alternatively set ``VIDEO_PROVIDER`` to ``file:./providers/foo.json`` or a path
      ending in ``.json`` that exists under the repo — loads the same JSON schema.
    """
    load_dotenv()
    raw = os.environ.get("VIDEO_PROVIDER", "mock").strip()
    key = raw.lower()

    if key == "custom":
        return load_configurable_provider()

    if key in _BUILTIN and key != "custom":
        if key == "mock":
            return MockVideoProvider()
        if key == "replicate":
            return ReplicateVideoProvider()
        if key == "xai":
            return XaiVideoProvider()
        if key == "openrouter":
            return OpenRouterVideoProvider()

    path = _resolve_config_path(raw)
    if path is not None:
        return ConfigurableHttpProvider.from_file(path)

    raise ValueError(
        f"Unknown VIDEO_PROVIDER={raw!r}. Use mock, replicate, xai, openrouter, custom "
        f"(with STUDIO_PROVIDER_CONFIG), or file:path/to/provider.json — see providers/README.md"
    )
