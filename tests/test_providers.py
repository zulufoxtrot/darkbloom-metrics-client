import pytest

from darkbloom_metrics.providers import PROVIDER_SENSORS, provider_label
from darkbloom_metrics.privy import PrivyAuth, jwt_exp, jwt_aud

PROVIDER = {
    "status": "serving",
    "online": True,
    "hardware": {"chip_name": "Apple M2 Ultra", "chip_tier": "Ultra", "memory_gb": 192},
    "pending_requests": 1,
    "max_concurrency": 24,
    "lifetime_requests_served": 140418,
    "lifetime_tokens_generated": 25489462,
    "reputation": {
        "score": 0.9614560069536415,
        "total_jobs": 133084,
        "successful_jobs": 132855,
        "failed_jobs": 229,
        "total_uptime_seconds": 793762,
        "avg_response_time_ms": 4359,
        "challenges_passed": 2659,
        "challenges_failed": 7,
    },
}


def test_provider_label():
    assert provider_label(PROVIDER) == "Darkbloom Apple M2 Ultra"
    m5 = {"hardware": {"chip_name": "Apple M5", "chip_tier": "Base"}}
    assert provider_label(m5) == "Darkbloom Apple M5"


def test_provider_entity_ids():
    by = {s.name_suffix: s for s in PROVIDER_SENSORS}
    assert by["Reputation"].entity_id("Darkbloom Apple M2 Ultra") == "sensor.darkbloom_apple_m2_ultra_reputation"
    assert by["Pending Requests"].entity_id("Darkbloom Apple M2 Ultra") == "sensor.darkbloom_apple_m2_ultra_pending_requests"


def test_provider_extraction():
    by = {s.name_suffix: s for s in PROVIDER_SENSORS}
    assert by["Reputation"].extract(PROVIDER) == pytest.approx(0.9614560)
    assert by["Pending Requests"].extract(PROVIDER) == 1
    assert by["Max Concurrency"].extract(PROVIDER) == 24
    assert by["Failed Jobs"].extract(PROVIDER) == 229
    assert by["Avg Response Time"].extract(PROVIDER) == 4359
    assert by["Challenges Passed"].extract(PROVIDER) == 2659


def test_jwt_parsing():
    # header.payload.signature with payload from the real privy token shape
    tok = "a.eyJzdWIiOiJ4IiwiYXVkIjoiYXBwMTIzIiwiZXhwIjoxNzg5NTAzNjU1fQ.c"
    assert jwt_aud(tok) == "app123"
    assert jwt_exp(tok) == 1789503655.0


def test_privy_auth_expired_no_refresh():
    auth = PrivyAuth(access_token="a.eyJleHAiOjF9.c")
    with pytest.raises(Exception):
        auth.get_token()


def test_privy_auth_valid_token():
    future = 4102444800  # 2100
    tok = f"a.{__import__('base64').urlsafe_b64encode(b'{\"exp\":%d}' % future).decode().rstrip('=')}.c"
    auth = PrivyAuth(access_token=tok)
    assert auth.get_token() == tok
