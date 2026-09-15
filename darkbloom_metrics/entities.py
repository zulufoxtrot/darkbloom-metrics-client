"""Sensor definitions mirroring the HA rest.yaml templates, one per entity.

Each sensor converts a fetched JSON payload into a value (or ``None`` when
unavailable, mirroring the ``availability:`` templates).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

from .naming import entity_id_for, model_display_name


@dataclass(frozen=True)
class SensorDef:
    name: str
    unit: str | None
    state_class: str | None
    icon: str
    extract: Callable[[dict[str, Any]], Any]

    @property
    def entity_id(self) -> str:
        return entity_id_for(self.name)


def _nu(key: str, scale: float = 100.0, rnd: int = 1) -> Callable[[dict], float | None]:
    def extract(stats: dict) -> float | None:
        nu = stats.get("network_utilization")
        if nu is None or key not in nu:
            return None
        return round(nu[key] * scale, rnd)

    return extract


def _stats(key: str, rnd: int | None = None) -> Callable[[dict], float | None]:
    def extract(stats: dict) -> float | None:
        if key not in stats:
            return None
        v = stats[key]
        if rnd is not None:
            v = round(float(v), rnd)
        return v

    return extract


def _evidence_coverage(stats: dict) -> float | None:
    if "application_evidence_providers" not in stats or "active_providers" not in stats:
        return None
    if not stats["active_providers"]:
        return None
    return round(stats["application_evidence_providers"] / stats["active_providers"] * 100, 1)


def _memory_tb(stats: dict) -> float | None:
    if "total_memory_gb" not in stats:
        return None
    return round(stats["total_memory_gb"] / 1024, 1)


def _bandwidth_tb(stats: dict) -> float | None:
    if "total_bandwidth_gbs" not in stats:
        return None
    return round(stats["total_bandwidth_gbs"] / 1024, 1)


def _countries(stats: dict) -> int | None:
    locs = stats.get("provider_locations")
    if locs is None:
        return None
    return len({l["country"] for l in locs})


def _cities(stats: dict) -> int | None:
    locs = stats.get("provider_locations")
    if locs is None:
        return None
    return len({l["city"] for l in locs})


def _regions(stats: dict) -> int | None:
    regs = stats.get("request_regions")
    if regs is None:
        return None
    return len({r["region"] for r in regs})


def _top_provider_country(stats: dict) -> str | None:
    locs = stats.get("provider_locations")
    if locs is None:
        return None
    totals: dict[str, int] = {}
    for l in locs:
        totals[l["country"]] = totals.get(l["country"], 0) + l["providers"]
    if not totals:
        return None
    return max(totals, key=lambda k: totals[k])


def _top_provider_country_providers(stats: dict) -> int | None:
    locs = stats.get("provider_locations")
    if locs is None:
        return None
    totals: dict[str, int] = {}
    for l in locs:
        totals[l["country"]] = totals.get(l["country"], 0) + l["providers"]
    return max(totals.values()) if totals else None


def _top_request_region(stats: dict) -> str | None:
    regs = stats.get("request_regions")
    if regs is None:
        return None
    if not regs:
        return None
    return max(regs, key=lambda r: r["requests"])["region"]


def _top_request_region_requests(stats: dict) -> int | None:
    regs = stats.get("request_regions")
    if regs is None:
        return None
    if not regs:
        return None
    return max(regs, key=lambda r: r["requests"])["requests"]


STATS_SENSORS: list[SensorDef] = [
    SensorDef("Darkbloom Network Utilization", "%", "measurement", "mdi:gauge", _nu("utilization")),
    SensorDef("Darkbloom Warm Utilization", "%", "measurement", "mdi:gauge", _nu("warm_utilization")),
    SensorDef("Darkbloom Token Budget Utilization", "%", "measurement", "mdi:gauge", _nu("token_budget_utilization", rnd=2)),
    SensorDef("Darkbloom Bottleneck Utilization", "%", "measurement", "mdi:gauge", _nu("bottleneck_utilization")),
    SensorDef("Darkbloom Bottleneck Model", None, None, "mdi:alert-circle-outline", lambda s: s.get("network_utilization", {}).get("bottleneck_model")),
    SensorDef("Darkbloom Network Capacity TPS", "tokens/s", "measurement", "mdi:speedometer", _stats("network_capacity_tps", rnd=1)),
    SensorDef("Darkbloom Network Active Requests", "requests", "measurement", "mdi:swap-horizontal", _nu("active_requests", scale=1, rnd=0)),
    SensorDef("Darkbloom Network Queued Requests", "requests", "measurement", "mdi:clock-fast", _nu("queued_requests", scale=1, rnd=0)),
    SensorDef("Darkbloom Active Providers", "providers", "measurement", "mdi:server-network", _stats("active_providers")),
    SensorDef("Darkbloom Attested Providers", "providers", "measurement", "mdi:certificate-outline", _stats("code_attested_providers")),
    SensorDef("Darkbloom Network Power Draw", "W", "measurement", None, _stats("active_power_watts")),
    SensorDef("Darkbloom Requests Last 24h", "requests", "measurement", "mdi:counter", _stats("last_24h_requests")),
    SensorDef("Darkbloom Total Tokens Last 24h", "tokens", "measurement", "mdi:token", _stats("last_24h_total_tokens")),
    SensorDef("Darkbloom Prompt Tokens Last 24h", "tokens", "measurement", "mdi:token", _stats("last_24h_prompt_tokens")),
    SensorDef("Darkbloom Completion Tokens Last 24h", "tokens", "measurement", "mdi:token", _stats("last_24h_completion_tokens")),
    SensorDef("Darkbloom Avg Tokens Per Request", "tokens", "measurement", "mdi:chart-line", _stats("avg_tokens_per_request", rnd=0)),
    SensorDef("Darkbloom Total Requests All-Time", "requests", "total_increasing", "mdi:database-outline", _stats("total_requests")),
    SensorDef("Darkbloom Total Tokens All-Time", "tokens", "total_increasing", "mdi:database-outline", _stats("total_tokens")),
    SensorDef("Darkbloom Total GPU Cores", "cores", "measurement", "mdi:expansion-card", _stats("total_gpu_cores")),
    SensorDef("Darkbloom Total Provider Memory", "TB", "measurement", "mdi:memory", _memory_tb),
    SensorDef("Darkbloom Total Bandwidth", "TB", "measurement", "mdi:network", _bandwidth_tb),
    SensorDef("Darkbloom Total CPU Cores", "cores", "measurement", "mdi:cpu-64-bit", _stats("total_cpu_cores")),
    SensorDef("Darkbloom Total Prompt Tokens All-Time", "tokens", "total_increasing", "mdi:token", _stats("total_prompt_tokens")),
    SensorDef("Darkbloom Total Completion Tokens All-Time", "tokens", "total_increasing", "mdi:token", _stats("total_completion_tokens")),
    SensorDef("Darkbloom Evidence Attested Providers", "providers", "measurement", "mdi:certificate-outline", _stats("application_evidence_providers")),
    SensorDef("Darkbloom Evidence Coverage", "%", "measurement", "mdi:certificate-outline", _evidence_coverage),
    SensorDef("Darkbloom Provider Countries", "countries", "measurement", "mdi:earth", _countries),
    SensorDef("Darkbloom Provider Cities", "cities", "measurement", "mdi:city-variant-outline", _cities),
    SensorDef("Darkbloom Request Regions", "regions", "measurement", "mdi:map-marker-multiple-outline", _regions),
    SensorDef("Darkbloom Top Provider Country", None, None, "mdi:earth", _top_provider_country),
    SensorDef("Darkbloom Top Provider Country Providers", "providers", "measurement", "mdi:earth", _top_provider_country_providers),
    SensorDef("Darkbloom Top Request Region", None, None, "mdi:map-marker", _top_request_region),
    SensorDef("Darkbloom Top Request Region Requests", "requests", "measurement", "mdi:map-marker", _top_request_region_requests),
]

STATS_BINARY_SENSORS: list[SensorDef] = [
    SensorDef("Darkbloom Code Attestation Enforced", None, None, "mdi:shield-check-outline", lambda s: s.get("code_attestation_enforced")),
]

# Per-model capacity sensors (fields on each entry of capacity.models[]).
MODEL_SENSORS: list[SensorDef] = [
    SensorDef("Active Requests", "requests", "measurement", "mdi:swap-horizontal", lambda m: m.get("active_requests")),
    SensorDef("Queued Requests", "requests", "measurement", "mdi:clock-fast", lambda m: m.get("queued_requests")),
    SensorDef("Aggregate TPS", "tokens/s", "measurement", "mdi:speedometer", lambda m: round(m.get("aggregate_tps", 0.0), 1)),
    SensorDef("Estimated TTFT", "s", "measurement", "mdi:timer-outline", lambda m: round(m.get("estimated_ttft_ms", 0.0) / 1000, 1)),
    SensorDef("Token Budget Remaining", "%", "measurement", "mdi:token", lambda m: round(m["token_budget_remaining"] / m["token_budget_total"] * 100, 1)),
    SensorDef("Routable Providers", "providers", "measurement", "mdi:server-network", lambda m: m.get("routable_providers")),
    SensorDef("Warm Providers", "providers", "measurement", "mdi:fire", lambda m: m.get("warm_providers")),
    SensorDef("Running Providers", "providers", "measurement", "mdi:play-network", lambda m: m.get("running_providers")),
    SensorDef("Cold Providers", "providers", "measurement", "mdi:snowflake", lambda m: m.get("cold_providers")),
]

MODEL_QUEUE_FULLNESS = SensorDef(
    "Queue Fullness", "%", "measurement", "mdi:queue-size",
    lambda m: math.floor(m["queued_requests"] / m["queue_limit"] * 100 + 0.5),
)

MODEL_BINARY_SENSORS: list[SensorDef] = [
    SensorDef("Can Accept", None, None, "mdi:check-circle-outline", lambda m: m.get("can_accept")),
]
