"""Button platform for Duosida Wallbox."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ID_TAG, DEFAULT_ID_TAG, DOMAIN
from .coordinator import DuosidaDataUpdateCoordinator
from .entity import DuosidaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Duosida buttons."""
    coordinator: DuosidaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DuosidaRefreshButton(coordinator),
            DuosidaStartButton(coordinator),
            DuosidaStopButton(coordinator),
        ]
    )


class DuosidaRefreshButton(DuosidaEntity, ButtonEntity):
    """Manual refresh button."""

    _attr_translation_key = "refresh"

    def __init__(self, coordinator: DuosidaDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "refresh")

    async def async_press(self) -> None:
        """Refresh charger state."""
        await self.coordinator.async_command_refresh()


class DuosidaStartButton(DuosidaEntity, ButtonEntity):
    """Start charging button."""

    _attr_translation_key = "start_charging"

    def __init__(self, coordinator: DuosidaDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "start_charging")

    async def async_press(self) -> None:
        """Start charging."""
        id_tag = self.coordinator.config_entry.data.get(CONF_ID_TAG, DEFAULT_ID_TAG)
        await self.coordinator.async_start_charging(str(id_tag))


class DuosidaStopButton(DuosidaEntity, ButtonEntity):
    """Stop charging button."""

    _attr_translation_key = "stop_charging"

    def __init__(self, coordinator: DuosidaDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "stop_charging")

    async def async_press(self) -> None:
        """Stop charging."""
        transaction_id = self.raw_value("transaction_id") or self.raw_value("vendor_transactionId")
        try:
            parsed_transaction_id = int(transaction_id) if transaction_id is not None else None
        except (TypeError, ValueError):
            parsed_transaction_id = None
        await self.coordinator.async_stop_charging(parsed_transaction_id)
