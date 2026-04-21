from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Directory containing pyproject.toml (walks upward from this package)."""
    p = Path(__file__).resolve()
    for parent in [p.parent] + list(p.parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("Could not locate project root (pyproject.toml). Run the CLI from the ai-movie-studio repo.")


def schema_path(name: str) -> Path:
    return repo_root() / "schemas" / name


def load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(repo_root() / ".env")
    except ImportError:
        pass


def env_provider() -> str:
    return os.environ.get("VIDEO_PROVIDER", "mock").strip().lower()
