#!/usr/bin/with-contenv bashio

set -e

read_config() {
  local key="$1"
  local fallback="$2"

  python3 - "$key" "$fallback" <<'PY'
import json
import sys
from pathlib import Path

key, fallback = sys.argv[1], sys.argv[2]
try:
    options = json.loads(Path("/data/options.json").read_text())
except Exception:
    options = {}
value = options.get(key, fallback)
print(value)
PY
}

CHARGER_HOST="$(read_config 'charger_host' '192.168.7.140')"
POLL_INTERVAL="$(read_config 'poll_interval' '30')"
PROBE_DURATION="$(read_config 'probe_duration' '8')"

bashio::log.info "Starting Duosida Wallbox dashboard"
bashio::log.info "Charger host: ${CHARGER_HOST}"
bashio::log.info "Poll interval: ${POLL_INTERVAL}s, probe duration: ${PROBE_DURATION}s"

exec python3 /opt/duosida/duosida_web.py \
  --charger-host "${CHARGER_HOST}" \
  --listen "0.0.0.0" \
  --port "8765" \
  --interval "${POLL_INTERVAL}" \
  --probe-duration "${PROBE_DURATION}"
