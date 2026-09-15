"""Entity naming compatible with Home Assistant's REST sensors.

Grafana dashboards query InfluxDB measurements by ``entity_id`` tag values
derived from HA display names. To keep dashboards working, this module
reproduces HA's slugify (lowercase, accents removed, non-alphanumerics
collapsed to ``_``) and the display-name conventions used in rest.yaml.
"""

from __future__ import annotations

import re
import unicodedata

# Model id -> HA display name, matching rest.yaml exactly. Grafana panels and
# existing Influx series depend on these; do not change for existing models.
KNOWN_MODEL_NAMES: dict[str, str] = {
    "qwen3.5-35b-a3b": "Qwen3.5 35B",
    "gemma-4-26b-8bit": "Gemma 4 26B 8-bit",
    "qwen3.6-35b-a3b-vl-mtp-mxfp8": "Qwen3.6 35B VL",
    "gpt-oss-20b": "GPT-OSS 20B",
    "qwen3-vl-30b-a3b-instruct": "Qwen3-VL 30B",
    "gemma-4-26b-qat-4bit": "Gemma 4 26B QAT 4-bit",
    "Qwen3.5-9B": "Qwen3.5 9B",
    "EigenLabs/Qwen3.8-27B-4bit-mtp": "Qwen3.8 27B",
}

_FALLBACK_ACRONYMS = {"vl": "VL", "mtp": "MTP", "a3b": "A3B"}

# Pretty labels for models whose auto-generated display name is ugly.
# Used only in friendly_name_str (Influx field); entity ids/slug stay derived
# from the display name so existing Grafana series are unaffected.
MODEL_LABEL_OVERRIDES: dict[str, str] = {
    "nvidia-nemotron-3.5-lightning": "Nemotron 3.5 Lightning",
}


def model_friendly_name(model_id: str) -> str:
    """Pretty label for a model id (used for friendly_name_str / legends)."""
    if model_id in MODEL_LABEL_OVERRIDES:
        return MODEL_LABEL_OVERRIDES[model_id]
    return model_display_name(model_id)


def slugify(name: str) -> str:
    """Slugify a display name the way Home Assistant does.

    "Gemma 4 26B 8-bit" -> "gemma_4_26b_8_bit"
    "Qwen3.6 35B VL"    -> "qwen3_6_35b_vl"
    """
    text = unicodedata.normalize("NFKD", name)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def model_display_name(model_id: str) -> str:
    """Display name for a model id; auto-generates one for unknown models."""
    if model_id in KNOWN_MODEL_NAMES:
        return KNOWN_MODEL_NAMES[model_id]
    # Strip org prefix and quantization suffixes, prettify the rest.
    short = model_id.split("/")[-1]
    short = re.sub(r"-(mtp|mxfp8|4bit|8bit|qat|instruct)", "", short)
    words = [w for w in re.split(r"[-_.]+", short) if w]
    pretty = " ".join(_FALLBACK_ACRONYMS.get(w.lower(), w) for w in words)
    return pretty


def entity_id_for(display_name: str) -> str:
    """Full HA-style entity id object for a sensor display name."""
    return f"sensor.{slugify(display_name)}"
