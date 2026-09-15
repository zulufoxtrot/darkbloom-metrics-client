"""Darkbloom console API client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .privy import PrivyAuth

log = logging.getLogger(__name__)

CAPACITY_URL = "https://console.darkbloom.dev/api/models/capacity"
STATS_URL = "https://console.darkbloom.dev/api/stats"
PROVIDERS_URL = "https://console.darkbloom.dev/api/me/providers"


class DarkbloomClient:
    def __init__(
        self,
        capacity_url: str = CAPACITY_URL,
        stats_url: str = STATS_URL,
        providers_url: str = PROVIDERS_URL,
        timeout: float = 60.0,
        privy: PrivyAuth | None = None,
    ) -> None:
        self.capacity_url = capacity_url
        self.stats_url = stats_url
        self.providers_url = providers_url
        self.privy = privy
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

    def fetch_providers(self) -> list[dict[str, Any]]:
        """Return the user's own providers[] (reputation, concurrency). Requires Privy auth."""
        if self.privy is None:
            raise RuntimeError("providers endpoint requires Privy auth (set PRIVY_ACCESS_TOKEN)")
        r = self._http.get(self.providers_url, headers={"authorization": f"Bearer {self.privy.get_token()}"})
        if r.status_code == 401:
            # force refresh and retry once
            self.privy.access_token = None
            r = self._http.get(self.providers_url, headers={"authorization": f"Bearer {self.privy.get_token()}"})
        r.raise_for_status()
        providers = r.json().get("providers", [])
        log.debug("providers: %d entries", len(providers))
        return providers

    def close(self) -> None:
        self._http.close()
        if self.privy:
            self.privy.close()
