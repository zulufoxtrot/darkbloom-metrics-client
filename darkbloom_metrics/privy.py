"""Privy session auth for console.darkbloom.dev.

The /api/me/providers endpoint requires an interactive Privy session token
(API keys are rejected). The access token is a short-lived JWT (typically 1h).
Supports two modes:

- static access token (PRIVY_ACCESS_TOKEN) — expires hourly, loud failure
- refresh token (PRIVY_REFRESH_TOKEN) — long-lived, exchanged for fresh
  access tokens via auth.privy.io
"""

from __future__ import annotations

import base64
import json
import logging
import time

import httpx

log = logging.getLogger(__name__)

PRIVY_REFRESH_URL = "https://auth.privy.io/api/v1/refresh"
REFRESH_MARGIN_S = 120


class AuthError(Exception):
    pass


def jwt_exp(token: str) -> float:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return float(json.loads(base64.urlsafe_b64decode(payload))["exp"])
    except Exception:
        return 0.0


def jwt_aud(token: str) -> str | None:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("aud")
    except Exception:
        return None


class PrivyAuth:
    def __init__(
        self,
        access_token: str | None = None,
        refresh_token: str | None = None,
        app_id: str | None = None,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.app_id = app_id or (jwt_aud(access_token) if access_token else None)
        self._http = httpx.Client(
            timeout=15.0,
            headers={
                "privy-app-id": self.app_id or "",
                "privy-client": "python-metrics/1.0",
                "content-type": "application/json",
            },
        )

    def _refresh(self) -> None:
        if not self.refresh_token:
            raise AuthError(
                "PRIVY_ACCESS_TOKEN expired and no PRIVY_REFRESH_TOKEN configured — "
                "re-extract the token from the browser (console.darkbloom.dev devtools)"
            )
        r = self._http.post(PRIVY_REFRESH_URL, json={"refresh_token": self.refresh_token})
        if r.status_code != 200:
            raise AuthError(f"privy refresh failed ({r.status_code}): {r.text[:200]} — "
                            "refresh token likely expired; re-extract from the browser")
        data = r.json()
        self.access_token = data.get("token")
        new_refresh = data.get("refresh_token") or data.get("refresh_token_expires_in")
        if data.get("refresh_token"):
            self.refresh_token = data["refresh_token"]
            log.info("privy refresh token rotated")
        if not self.access_token:
            raise AuthError(f"privy refresh returned no token: {str(data)[:200]}")

    def get_token(self) -> str:
        if not self.access_token:
            self._refresh()
        elif jwt_exp(self.access_token) < time.time() + REFRESH_MARGIN_S:
            log.info("privy access token near expiry, refreshing")
            try:
                self._refresh()
            except AuthError:
                if jwt_exp(self.access_token) > time.time():
                    log.warning("privy refresh failed but access token still valid; using it")
                else:
                    raise
        return self.access_token

    def close(self) -> None:
        self._http.close()
