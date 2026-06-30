"""Binary sensor platform for Duosida Wallbox."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import DuosidaDataUpdateCoordinator
from .entity import DuosidaEntity


@dataclass(frozen=True, kw_only=True)
class DuosidaBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Duosida binary sensor."""

    on_values: frozenset[str]


BINARY_SENSORS: tuple[DuosidaBinarySensorEntityDescription, ...] = (
    DuosidaBinarySensorEntityDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        on_values=frozenset({"true"}),
    ),
    DuosidaBinarySensorEntityDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        on_values=frozenset({"charging"}),
    ),
    DuosidaBinarySensorEntityDescription(
        key="fault",
        translation_key="fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        on_values=frozenset({"faulted"}),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Duosida binary sensors."""
    coordinator: DuosidaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(DuosidaBinarySensor(coordinator, description) for description in BINARY_SENSORS)


class DuosidaBinarySensor(DuosidaEntity, BinarySensorEntity):
    """Duosida binary sensor entity."""

    entity_description: DuosidaBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: DuosidaDataUpdateCoordinator,
        description: DuosidaBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Return binary sensor state."""
        if self.entity_description.key == "online":
            return bool(self.coordinator.data and self.coordinator.data.ok)
        if self.entity_description.key == "charging":
            value = self.value("status_status") or self.value("vendor_status")
        elif self.entity_description.key == "fault":
            value = self.value("status_status") or self.value("vendor_status")
        else:
            value = self.value()
        return str(value).lower() in self.entity_description.on_values
