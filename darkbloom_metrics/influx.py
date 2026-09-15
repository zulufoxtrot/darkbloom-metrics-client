"""InfluxDB point building, byte-compatible with HA's influxdb integration (v1)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from .entities import MODEL_BINARY_SENSORS, MODEL_QUEUE_FULLNESS, MODEL_SENSORS, STATS_BINARY_SENSORS, STATS_SENSORS, SensorDef

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class InfluxSettings:
    host: str = "localhost"
    port: int = 8086
    database: str = "homeassistant"
    username: str = "homeassistant"
    password: str = "homeassistant"

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class Writer:
    def __init__(self, settings: InfluxSettings) -> None:
        self._client = InfluxDBClient(
            url=settings.url,
            token=f"{settings.username}:{settings.password}",
            org="-",
        )
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
        self._bucket = settings.database

    def close(self) -> None:
        self._write_api.close()
        self._client.close()

    def _write(self, point: Point) -> None:
        self._write_api.write(bucket=self._bucket, record=point, write_precision=WritePrecision.NS)

    @staticmethod
    def _numeric_point(sensor: SensorDef, entity_id: str, value: float, display_name: str | None = None) -> Point:
        p = (
            Point(sensor.unit)
            .tag("domain", "sensor")
            .tag("entity_id", entity_id.removeprefix("sensor."))
            .field("value", float(value))
        )
        if display_name:
            p = p.field("friendly_name_str", display_name)
        if sensor.state_class:
            p = p.field("state_class_str", sensor.state_class)
        if sensor.icon:
            p = p.field("icon_str", sensor.icon)
        return p

    @staticmethod
    def _state_point(entity_id: str, state: Any, icon: str | None = None, display_name: str | None = None) -> Point:
        p = (
            Point(entity_id)
            .tag("domain", entity_id.split(".")[0])
            .tag("entity_id", entity_id.split(".", 1)[1])
            .field("state", str(state))
        )
        if display_name:
            p = p.field("friendly_name_str", display_name)
        if icon:
            p = p.field("icon_str", icon)
        return p

    def write_capacity(self, models: list[dict[str, Any]], display_names: dict[str, str]) -> None:
        points: list[Point] = []
        for model in models:
            mid = model["id"]
            if "token_budget_remaining" not in model or not model.get("token_budget_total"):
                log.warning("model %s missing token budget fields; skipping", mid)
                continue
            display = display_names.get(mid, mid)
            from .naming import model_friendly_name
            label_base = f"Darkbloom {model_friendly_name(mid)}"
            for sensor in MODEL_SENSORS:
                value = sensor.extract(model)
                if value is None:
                    continue
                points.append(self._numeric_point(sensor, _entity_for_name(f"{display} {sensor.name}"), value, f"{label_base} {sensor.name}"))
            for sensor in MODEL_BINARY_SENSORS:
                value = sensor.extract(model)
                if value is None:
                    continue
                points.append(self._state_point(_entity_for_name(f"binary_sensor {display} {sensor.name}", prefix=False), "on" if value else "off", sensor.icon, f"{label_base} {sensor.name}"))
            qf = MODEL_QUEUE_FULLNESS.extract(model)
            if qf is not None and model.get("queue_limit"):
                points.append(self._numeric_point(MODEL_QUEUE_FULLNESS, _entity_for_name(f"{display} Queue Fullness"), qf, f"{label_base} Queue Fullness"))
        self._write_points(points, "capacity")

    def write_stats(self, stats: dict[str, Any]) -> None:
        points: list[Point] = []
        for sensor in STATS_SENSORS:
            value = sensor.extract(stats)
            if value is None:
                continue
            if sensor.unit is None:
                points.append(self._state_point(sensor.entity_id, value, sensor.icon, sensor.name))
            else:
                points.append(self._numeric_point(sensor, sensor.entity_id, value, sensor.name))
        for sensor in STATS_BINARY_SENSORS:
            value = sensor.extract(stats)
            if value is None:
                continue
            eid = sensor.entity_id.replace("sensor.", "binary_sensor.", 1)
            points.append(self._state_point(eid, "on" if value else "off", sensor.icon, sensor.name))
        self._write_points(points, "stats")

    def _write_points(self, points: list[Point], source: str) -> None:
        if not points:
            return
        try:
            self._write_api.write(bucket=self._bucket, record=points, write_precision=WritePrecision.NS)
            log.debug("wrote %d points (%s)", len(points), source)
        except Exception:
            log.exception("failed to write %d points (%s)", len(points), source)


def _entity_for_name(name: str, prefix: bool = True) -> str:
    from .naming import slugify

    if prefix:
        return f"sensor.{slugify(name)}"
    domain, rest = name.split(" ", 1)
    return f"{domain}.{slugify(rest)}"
