"""Switch platform for Duosida Wallbox."""

from __future__ import annotations

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
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
    """Set up Duosida switches."""
    coordinator: DuosidaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DuosidaChargingSwitch(coordinator)])


class DuosidaChargingSwitch(DuosidaEntity, SwitchEntity):
    """Charging start/stop switch."""

    _attr_translation_key = "charging"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: DuosidaDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "charging_switch")

    @property
    def is_on(self) -> bool:
        """Return whether charging is active."""
        status = self.value("status_status") or self.value("vendor_status")
        return str(status).lower() == "charging"

    async def async_turn_on(self, **kwargs) -> None:
        """Start charging."""
        id_tag = self.coordinator.config_entry.data.get(CONF_ID_TAG, DEFAULT_ID_TAG)
        await self.coordinator.async_start_charging(str(id_tag))

    async def async_turn_off(self, **kwargs) -> None:
        """Stop charging."""
        transaction_id = self.value("transaction_id") or self.value("vendor_transactionId")
        try:
            parsed_transaction_id = int(transaction_id) if transaction_id is not None else None
        except (TypeError, ValueError):
            parsed_transaction_id = None
        await self.coordinator.async_stop_charging(parsed_transaction_id)
