"""Number platform for Duosida Wallbox."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import DuosidaDataUpdateCoordinator
from .entity import DuosidaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Duosida number entities."""
    coordinator: DuosidaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DuosidaMaxCurrentNumber(coordinator)])


class DuosidaMaxCurrentNumber(DuosidaEntity, NumberEntity):
    """Maximum charging current number entity."""

    _attr_translation_key = "max_current"
    _attr_native_min_value = 6
    _attr_native_max_value = 32
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: DuosidaDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "max_current")

    @property
    def native_value(self) -> float | None:
        """Return current max current value."""
        for key in ("config_maxWorkCurrent", "current_offered", "current_import"):
            value = self.value(key)
            try:
                current = round(float(value))
            except (TypeError, ValueError):
                continue
            return max(6, min(32, current))
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set maximum charging current."""
        current = max(6, min(32, round(value)))
        await self.coordinator.async_set_max_current(current)
