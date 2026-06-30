"""Constants for the Duosida Wallbox integration."""

from __future__ import annotations

DOMAIN = "duosida_wallbox"

CONF_BASE_URL = "base_url"
CONF_ID_TAG = "id_tag"

DEFAULT_BASE_URL = "http://duosida_wallbox:8765"
DEFAULT_ID_TAG = "HA"
DEFAULT_SCAN_INTERVAL = 30

PLATFORMS = ["sensor", "binary_sensor", "number", "switch", "button"]
