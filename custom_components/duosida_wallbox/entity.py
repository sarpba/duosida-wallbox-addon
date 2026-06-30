"""Entity helpers for Duosida Wallbox."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DuosidaDataUpdateCoordinator


class DuosidaEntity(CoordinatorEntity[DuosidaDataUpdateCoordinator]):
    """Base entity for Duosida Wallbox."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DuosidaDataUpdateCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{self.serial}_{key}"

    @property
    def serial(self) -> str:
        """Return stable serial-like id for the charger."""
        return str(
            self.coordinator.values.get("chargePointSerialNumber")
            or self.coordinator.values.get("client_id")
            or self.coordinator.config_entry.unique_id
            or self.coordinator.config_entry.entry_id
        )

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return super().available and self.coordinator.data is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        values = self.coordinator.values
        return DeviceInfo(
            identifiers={(DOMAIN, self.serial)},
            manufacturer=str(values.get("chargePointVendor") or "Duosida"),
            model=str(values.get("chargePointModel") or "EV Wallbox"),
            name="Duosida Wallbox",
            serial_number=str(values.get("chargePointSerialNumber") or self.serial),
            sw_version=str(values.get("firmwareVersion")) if values.get("firmwareVersion") else None,
        )

    def value(self, key: str | None = None) -> Any:
        """Return raw charger data value."""
        return self.coordinator.values.get(key or self._key)
