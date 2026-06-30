"""Config flow for Duosida Wallbox."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DuosidaApiClient, DuosidaApiError
from .const import CONF_BASE_URL, CONF_ID_TAG, DEFAULT_BASE_URL, DEFAULT_ID_TAG, DOMAIN


class DuosidaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Duosida Wallbox."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = str(user_input[CONF_BASE_URL]).strip().rstrip("/")
            client = DuosidaApiClient(async_get_clientsession(self.hass), base_url)
            try:
                state = await client.async_get_state()
            except DuosidaApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(base_url)
                self._abort_if_unique_id_configured()
                data = {
                    CONF_BASE_URL: base_url,
                    CONF_ID_TAG: str(user_input.get(CONF_ID_TAG) or DEFAULT_ID_TAG),
                }
                title = state.data.get("chargePointSerialNumber") or state.data.get("chargePointModel") or "Duosida Wallbox"
                return self.async_create_entry(title=str(title), data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
                vol.Optional(CONF_ID_TAG, default=DEFAULT_ID_TAG): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
