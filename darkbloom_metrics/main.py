"""darkbloom-metrics-client entrypoint."""

from __future__ import annotations

import logging
import os
import signal
import threading

from .client import CAPACITY_URL, PROVIDERS_URL, STATS_URL, DarkbloomClient
from .influx import InfluxSettings, Writer
from .naming import model_display_name
from .privy import PrivyAuth, jwt_aud

log = logging.getLogger("darkbloom_metrics")

POLL_CAPACITY_S = int(os.getenv("DARKBLOOM_CAPACITY_INTERVAL", "10"))
POLL_STATS_S = int(os.getenv("DARKBLOOM_STATS_INTERVAL", "300"))
POLL_PROVIDERS_S = int(os.getenv("DARKBLOOM_PROVIDERS_INTERVAL", "60"))


def build_display_names(models: list[dict]) -> dict[str, str]:
    """Map model id -> display name (curated for known models, auto for new)."""
    return {model["id"]: f"Darkbloom {model_display_name(model['id'])}" for model in models}


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    capacity_url = os.getenv("DARKBLOOM_CAPACITY_URL", CAPACITY_URL)
    stats_url = os.getenv("DARKBLOOM_STATS_URL", STATS_URL)
    providers_url = os.getenv("DARKBLOOM_PROVIDERS_URL", PROVIDERS_URL)

    access_token = os.getenv("PRIVY_ACCESS_TOKEN")
    refresh_token = os.getenv("PRIVY_REFRESH_TOKEN")
    app_id = os.getenv("PRIVY_APP_ID") or (jwt_aud(access_token) if access_token else None)
    privy = PrivyAuth(access_token, refresh_token, app_id) if (access_token or refresh_token) else None

    settings = InfluxSettings(
        host=os.getenv("INFLUX_HOST", "localhost"),
        port=int(os.getenv("INFLUX_PORT", "8086")),
        database=os.getenv("INFLUX_DB", "homeassistant"),
        username=os.getenv("INFLUX_USERNAME", "homeassistant"),
        password=os.getenv("INFLUX_PASSWORD", "homeassistant"),
    )

    stop = threading.Event()

    def _sig(_a, _b):
        log.info("shutting down")
        stop.set()

    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)

    api = DarkbloomClient(capacity_url, stats_url, providers_url, privy=privy)
    writer = Writer(settings)

    last_stats = 0.0
    last_providers = 0.0
    log.info(
        "darkbloom-metrics-client started (capacity=%ds stats=%ds providers=%s/%ds -> %s/%s)",
        POLL_CAPACITY_S, POLL_STATS_S, "on" if privy else "off", POLL_PROVIDERS_S,
        settings.url, settings.database,
    )

    import time

    while not stop.is_set():
        now = time.monotonic()
        try:
            models = api.fetch_capacity()
            names = build_display_names(models)
            writer.write_capacity(models, names)
            log.info("capacity: %d models -> influx", len(models))
        except Exception:
            log.exception("capacity poll failed")
        if now - last_stats >= POLL_STATS_S:
            last_stats = now
            try:
                writer.write_stats(api.fetch_stats())
                log.info("stats -> influx")
            except Exception:
                log.exception("stats poll failed")
        if privy and now - last_providers >= POLL_PROVIDERS_S:
            last_providers = now
            try:
                providers = api.fetch_providers()
                writer.write_providers(providers)
                log.info("providers: %d -> influx", len(providers))
            except Exception as e:
                log.error("providers poll failed: %s", e)
        stop.wait(POLL_CAPACITY_S)

    writer.close()
    api.close()


if __name__ == "__main__":
    main()
