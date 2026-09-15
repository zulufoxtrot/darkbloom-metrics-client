# darkbloom-metrics-client

Standalone scraper for the [darkbloom](https://console.darkbloom.dev) network public API that pushes metrics to InfluxDB with the exact same schema as the Home Assistant `rest.yaml` integration it replaces — so existing Grafana dashboards work unchanged.

Replaces the HA scrape of:
- `https://console.darkbloom.dev/api/models/capacity` (poll 10s)
- `https://console.darkbloom.dev/api/stats` (poll 300s)

Models are **auto-discovered** from the capacity endpoint; no hardcoded model list. Known models reuse the historical display names (and thus Influx series/entity_ids); new models get auto-generated names.

## Influx schema (matches HA influxdb integration)

- Numeric sensors: measurement = unit of measurement (`requests`, `%`, `tokens/s`, `s`, `providers`, `tokens`, `W`, `cores`, `TB`), field `value`, tags `domain`/`entity_id`
- String/binary sensors: measurement = full entity id (`sensor.darkbloom_bottleneck_model`, `binary_sensor.darkbloom_..._can_accept`), field `state`

## Configuration (env vars)

| Variable | Default |
|---|---|
| `INFLUX_HOST` | `localhost` |
| `INFLUX_PORT` | `8086` |
| `INFLUX_DB` | `homeassistant` |
| `INFLUX_USERNAME` | `homeassistant` |
| `INFLUX_PASSWORD` | `homeassistant` |
| `DARKBLOOM_CAPACITY_URL` | `https://console.darkbloom.dev/api/models/capacity` |
| `DARKBLOOM_STATS_URL` | `https://console.darkbloom.dev/api/stats` |
| `DARKBLOOM_CAPACITY_INTERVAL` | `10` |
| `DARKBLOOM_STATS_INTERVAL` | `300` |
| `LOG_LEVEL` | `INFO` |
| `PRIVY_ACCESS_TOKEN` | *(empty)* — enables the provider metrics (reputation/concurrency) |
| `PRIVY_REFRESH_TOKEN` | *(empty)* — long-lived Privy refresh token; keeps provider metrics alive past access-token expiry |
| `DARKBLOOM_PROVIDERS_INTERVAL` | `60` |

Provider metrics come from `console.darkbloom.dev/api/me/providers`, which requires an interactive Privy session token (API keys rejected). Extract the access token (and ideally the Privy refresh token) from your browser's devtools while logged into the console; the client auto-refreshes when a refresh token is set.

## Run

```sh
docker run -d --network host \
  -e INFLUX_HOST=localhost -e INFLUX_PASSWORD=homeassistant \
  ghcr.io/zulufoxtrot/darkbloom-metrics-client:latest
```

Deployed in the `homeassistant` Portainer stack on gap.local.

## Development

```sh
uv sync
uv run pytest
```
