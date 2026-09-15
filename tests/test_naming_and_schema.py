from darkbloom_metrics.entities import MODEL_QUEUE_FULLNESS, MODEL_SENSORS, STATS_SENSORS
from darkbloom_metrics.influx import Writer


def test_slugify_matches_ha():
    from darkbloom_metrics.naming import slugify

    assert slugify("Gemma 4 26B 8-bit") == "gemma_4_26b_8_bit"
    assert slugify("Qwen3.6 35B VL") == "qwen3_6_35b_vl"
    assert slugify("Qwen3.5 35B") == "qwen3_5_35b"
    assert slugify("GPT-OSS 20B") == "gpt_oss_20b"
    assert slugify("Qwen3-VL 30B") == "qwen3_vl_30b"
    assert slugify("Gemma 4 26B QAT 4-bit") == "gemma_4_26b_qat_4_bit"
    assert slugify("Qwen3.5 9B") == "qwen3_5_9b"
    assert slugify("Qwen3.8 27B") == "qwen3_8_27b"


def test_model_display_names_match_ha():
    from darkbloom_metrics.naming import KNOWN_MODEL_NAMES, model_display_name

    assert model_display_name("qwen3.5-35b-a3b") == "Qwen3.5 35B"
    assert model_display_name("EigenLabs/Qwen3.8-27B-4bit-mtp") == "Qwen3.8 27B"
    assert model_display_name("new-model-42") not in KNOWN_MODEL_NAMES
    assert len(model_display_name("new-model-42")) > 0


def test_stats_sensor_entity_ids_match_ha():
    by_name = {s.name: s for s in STATS_SENSORS}
    assert by_name["Darkbloom Network Utilization"].entity_id == "sensor.darkbloom_network_utilization"
    assert by_name["Darkbloom Bottleneck Model"].entity_id == "sensor.darkbloom_bottleneck_model"
    assert by_name["Darkbloom Total Provider Memory"].entity_id == "sensor.darkbloom_total_provider_memory"
    assert by_name["Darkbloom Total Bandwidth"].entity_id == "sensor.darkbloom_total_bandwidth"

    from darkbloom_metrics.entities import STATS_BINARY_SENSORS
    binary = {s.name: s for s in STATS_BINARY_SENSORS}
    assert binary["Darkbloom Code Attestation Enforced"].entity_id == "sensor.darkbloom_code_attestation_enforced"


def test_numeric_point_schema_matches_ha_influx():
    sensor = next(s for s in STATS_SENSORS if s.name == "Darkbloom Network Active Requests")
    p = Writer._numeric_point(sensor, sensor.entity_id, 146.0)
    lp = p.to_line_protocol()
    assert lp.startswith("requests,domain=sensor,entity_id=darkbloom_network_active_requests ")
    assert 'state_class_str="measurement"' in lp
    assert "icon_str=" in lp
    assert "value=146" in lp


def test_state_point_schema_matches_ha_influx():
    sensor = next(s for s in STATS_SENSORS if s.name == "Darkbloom Bottleneck Model")
    p = Writer._state_point(sensor.entity_id, "Qwen3.5-9B", sensor.icon)
    lp = p.to_line_protocol()
    assert lp.startswith("sensor.darkbloom_bottleneck_model,domain=sensor,entity_id=darkbloom_bottleneck_model ")
    assert 'state="Qwen3.5-9B"' in lp
    assert "icon_str=" in lp


def test_binary_point():
    p = Writer._state_point("binary_sensor.darkbloom_gpt_oss_20b_can_accept", "on", "mdi:check-circle-outline")
    lp = p.to_line_protocol()
    assert lp.startswith("binary_sensor.darkbloom_gpt_oss_20b_can_accept,domain=binary_sensor,entity_id=darkbloom_gpt_oss_20b_can_accept ")
    assert 'state="on"' in lp


def test_capacity_model_extraction():
    model = {
        "id": "qwen3.5-35b-a3b",
        "active_requests": 2,
        "queued_requests": 1,
        "queue_limit": 8,
        "aggregate_tps": 1917.378,
        "estimated_ttft_ms": 165,
        "token_budget_remaining": 32161219,
        "token_budget_total": 32206718,
        "routable_providers": 41,
        "warm_providers": 22,
        "running_providers": 0,
        "cold_providers": 19,
    }
    values = {s.name: s.extract(model) for s in MODEL_SENSORS}
    assert values["Active Requests"] == 2
    assert values["Queued Requests"] == 1
    assert values["Aggregate TPS"] == 1917.4
    assert values["Estimated TTFT"] == 0.2  # HA template: (165/1000) round(1)
    assert values["Token Budget Remaining"] == 99.9  # (32161219/32206718*100) round(1)
    assert values["Routable Providers"] == 41
    assert MODEL_QUEUE_FULLNESS.extract(model) == 13  # 1/8*100 -> 12.5, Jinja round(0) -> 13


def test_stats_extraction():
    stats = {
        "network_utilization": {
            "utilization": 0.03590982,
            "warm_utilization": 0.03590982,
            "token_budget_utilization": 0.004521,
            "bottleneck_utilization": 0.28081,
            "bottleneck_model": "Qwen3.5-9B",
            "active_requests": 146,
            "queued_requests": 0,
        },
        "network_capacity_tps": 17556.3893,
        "active_providers": 300,
        "code_attested_providers": 250,
        "active_power_watts": 123456,
        "code_attestation_enforced": True,
        "provider_locations": [
            {"country": "Japan", "city": "Tokyo", "providers": 43},
            {"country": "Japan", "city": "Osaka", "providers": 10},
            {"country": "US", "city": "Austin", "providers": 5},
        ],
        "request_regions": [
            {"region": "Illinois", "requests": 735946},
            {"region": "Tokyo", "requests": 100},
        ],
        "total_memory_gb": 3612,
        "total_bandwidth_gbs": 2048,
        "application_evidence_providers": 100,
    }
    by_name = {s.name: s for s in STATS_SENSORS}
    assert by_name["Darkbloom Network Utilization"].extract(stats) == 3.6
    assert by_name["Darkbloom Token Budget Utilization"].extract(stats) == 0.45
    assert by_name["Darkbloom Network Active Requests"].extract(stats) == 146
    assert by_name["Darkbloom Bottleneck Model"].extract(stats) == "Qwen3.5-9B"
    assert by_name["Darkbloom Total Provider Memory"].extract(stats) == 3.5  # 3612/1024 round(1)
    assert by_name["Darkbloom Total Bandwidth"].extract(stats) == 2.0
    assert by_name["Darkbloom Provider Countries"].extract(stats) == 2
    assert by_name["Darkbloom Provider Cities"].extract(stats) == 3
    assert by_name["Darkbloom Request Regions"].extract(stats) == 2
    assert by_name["Darkbloom Top Provider Country"].extract(stats) == "Japan"
    assert by_name["Darkbloom Top Provider Country Providers"].extract(stats) == 53
    assert by_name["Darkbloom Top Request Region"].extract(stats) == "Illinois"
    assert by_name["Darkbloom Top Request Region Requests"].extract(stats) == 735946
    assert by_name["Darkbloom Evidence Coverage"].extract(stats) == 33.3
