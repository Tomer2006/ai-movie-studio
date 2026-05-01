"""Backward compatibility: ``MockVideoProvider`` was renamed to ``CustomVideoProvider``."""

from __future__ import annotations

from studio.providers.custom import CustomVideoProvider

MockVideoProvider = CustomVideoProvider

__all__ = ["MockVideoProvider"]
