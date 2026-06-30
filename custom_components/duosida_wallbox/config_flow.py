"""Config flow for Duosida Wallbox."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .const import (
    CONF_CHARGER_HOST,
    CONF_ID_TAG,
    CONF_PORT,
    CONF_PROBE_DURATION,
    DEFAULT_CHARGER_HOST,
    DEFAULT_ID_TAG,
    DEFAULT_PORT,
    DEFAULT_PROBE_DURATION,
    DOMAIN,
)


class DuosidaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Duosida Wallbox."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_CHARGER_HOST]).strip()
            port = int(user_input[CONF_PORT])
            probe_duration = int(user_input[CONF_PROBE_DURATION])
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()
            data = {
                CONF_CHARGER_HOST: host,
                CONF_PORT: port,
                CONF_PROBE_DURATION: probe_duration,
                CONF_ID_TAG: str(user_input.get(CONF_ID_TAG) or DEFAULT_ID_TAG),
            }
            return self.async_create_entry(title=f"Duosida Wallbox {host}", data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_CHARGER_HOST, default=DEFAULT_CHARGER_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(int, vol.Range(min=1, max=65535)),
                vol.Required(CONF_PROBE_DURATION, default=DEFAULT_PROBE_DURATION): vol.All(
                    int,
                    vol.Range(min=3, max=60),
                ),
                vol.Optional(CONF_ID_TAG, default=DEFAULT_ID_TAG): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
