"""Darkbloom console API client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)

CAPACITY_URL = "https://console.darkbloom.dev/api/models/capacity"
STATS_URL = "https://console.darkbloom.dev/api/stats"


class DarkbloomClient:
    def __init__(self, capacity_url: str = CAPACITY_URL, stats_url: str = STATS_URL, timeout: float = 60.0) -> None:
        self.capacity_url = capacity_url
        self.stats_url = stats_url
        self._http = httpx.Client(timeout=timeout, headers={"user-agent": "darkbloom-metrics-client/1.0"})

    def fetch_capacity(self) -> list[dict[str, Any]]:
        """Return the models[] array (auto-discovers available models)."""
        r = self._http.get(self.capacity_url)
        r.raise_for_status()
        models = r.json().get("models", [])
        log.debug("capacity: %d models", len(models))
        return models

    def fetch_stats(self) -> dict[str, Any]:
        r = self._http.get(self.stats_url)
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._http.close()
