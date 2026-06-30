"""Constants for the Duosida Wallbox integration."""

from __future__ import annotations

DOMAIN = "duosida_wallbox"

CONF_CHARGER_HOST = "charger_host"
CONF_ID_TAG = "id_tag"
CONF_PORT = "port"
CONF_PROBE_DURATION = "probe_duration"

DEFAULT_CHARGER_HOST = "192.168.7.140"
DEFAULT_ID_TAG = "HA"
DEFAULT_PORT = 9988
DEFAULT_PROBE_DURATION = 15
DEFAULT_SCAN_INTERVAL = 20

PLATFORMS = ["sensor", "binary_sensor", "number", "button"]
