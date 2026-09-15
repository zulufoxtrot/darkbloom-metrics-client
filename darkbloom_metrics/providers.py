"""Per-provider sensor defs for /api/me/providers (reputation, concurrency)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .entities import SensorDef
from .naming import slugify


@dataclass(frozen=True)
class ProviderSensorDef:
    """Sensor scoped to one of the account's providers (keyed by chip)."""

    name_suffix: str
    unit: str | None
    state_class: str | None
    icon: str
    extract: Callable[[dict[str, Any]], Any]

    def display(self, provider_label: str) -> str:
        return f"{provider_label} {self.name_suffix}"

    def entity_id(self, provider_label: str) -> str:
        return f"sensor.{slugify(self.display(provider_label))}"

    def binary_entity_id(self, provider_label: str) -> str:
        return f"binary_sensor.{slugify(self.display(provider_label))}"


def _reputation(key: str, default: float = 0.0) -> Callable[[dict], float]:
    def extract(p: dict) -> float:
        rep = p.get("reputation") or {}
        return rep.get(key, default)

    return extract


def _root(key: str) -> Callable[[dict], Any]:
    def extract(p: dict) -> Any:
        return p.get(key)

    return extract


PROVIDER_SENSORS: list[ProviderSensorDef] = [
    ProviderSensorDef("Reputation", "score", "measurement", "mdi:star-outline", _reputation("score")),
    ProviderSensorDef("Pending Requests", "requests", "measurement", "mdi:clock-fast", _root("pending_requests")),
    ProviderSensorDef("Max Concurrency", "requests", "measurement", "mdi:swap-horizontal", _root("max_concurrency")),
    ProviderSensorDef("Successful Jobs", "jobs", "total_increasing", "mdi:check-circle-outline", _reputation("successful_jobs")),
    ProviderSensorDef("Failed Jobs", "jobs", "total_increasing", "mdi:alert-circle-outline", _reputation("failed_jobs")),
    ProviderSensorDef("Avg Response Time", "ms", "measurement", "mdi:speedometer", _reputation("avg_response_time_ms")),
    ProviderSensorDef("Lifetime Requests", "requests", "total_increasing", "mdi:database-outline", _root("lifetime_requests_served")),
    ProviderSensorDef("Lifetime Tokens", "tokens", "total_increasing", "mdi:token", _root("lifetime_tokens_generated")),
    ProviderSensorDef("Total Jobs", "jobs", "total_increasing", "mdi:briefcase-outline", _reputation("total_jobs")),
    ProviderSensorDef("Uptime", "s", "total_increasing", "mdi:timer-outline", _reputation("total_uptime_seconds")),
    ProviderSensorDef("Challenges Passed", "challenges", "total_increasing", "mdi:shield-check-outline", _reputation("challenges_passed")),
    ProviderSensorDef("Challenges Failed", "challenges", "total_increasing", "mdi:shield-alert-outline", _reputation("challenges_failed")),
]

PROVIDER_BINARY_SENSORS: list[ProviderSensorDef] = [
    ProviderSensorDef("Online", None, None, "mdi:server-network", _root("online")),
]

PROVIDER_STATE_SENSORS: list[ProviderSensorDef] = [
    ProviderSensorDef("Status", None, None, "mdi:server", _root("status")),
]


def provider_label(p: dict[str, Any]) -> str:
    """Display label for a provider, e.g. 'Darkbloom Apple M2 Ultra'."""
    hw = p.get("hardware") or {}
    chip = hw.get("chip_name") or hw.get("chip_family") or "Unknown"
    tier = hw.get("chip_tier")
    name = f"{chip} {tier}" if tier and tier.lower() != "base" and tier.lower() not in chip.lower() else chip
    return f"Darkbloom {name}"
