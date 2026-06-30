"""Button platform for Duosida Wallbox."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import DuosidaDataUpdateCoordinator
from .entity import DuosidaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Duosida buttons."""
    coordinator: DuosidaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DuosidaRefreshButton(coordinator)])


class DuosidaRefreshButton(DuosidaEntity, ButtonEntity):
    """Manual refresh button."""

    _attr_translation_key = "refresh"

    def __init__(self, coordinator: DuosidaDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "refresh")

    async def async_press(self) -> None:
        """Refresh charger state."""
        await self.coordinator.async_command_refresh()
