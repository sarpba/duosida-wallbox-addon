"""Duosida Wallbox integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import DuosidaApiClient
from .const import (
    CONF_CHARGER_HOST,
    CONF_PORT,
    CONF_PROBE_DURATION,
    DEFAULT_PORT,
    DEFAULT_PROBE_DURATION,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import DuosidaDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Duosida Wallbox from a config entry."""
    client = DuosidaApiClient(
        host=entry.data[CONF_CHARGER_HOST],
        port=int(entry.data.get(CONF_PORT, DEFAULT_PORT)),
        probe_duration=int(entry.data.get(CONF_PROBE_DURATION, DEFAULT_PROBE_DURATION)),
    )
    coordinator = DuosidaDataUpdateCoordinator(hass, entry, client)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
