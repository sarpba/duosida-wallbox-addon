"""Sensor platform for Duosida Wallbox."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfFrequency, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .coordinator import DuosidaDataUpdateCoordinator
from .entity import DuosidaEntity


@dataclass(frozen=True, kw_only=True)
class DuosidaSensorEntityDescription(SensorEntityDescription):
    """Describes a Duosida sensor."""

    fallback_unit: str | None = None


SENSORS: tuple[DuosidaSensorEntityDescription, ...] = (
    DuosidaSensorEntityDescription(
        key="status_status",
        translation_key="charge_status",
    ),
    DuosidaSensorEntityDescription(
        key="status_errorCode",
        translation_key="error_code",
    ),
    DuosidaSensorEntityDescription(
        key="current_import",
        translation_key="current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DuosidaSensorEntityDescription(
        key="current_offered",
        translation_key="offered_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DuosidaSensorEntityDescription(
        key="voltage",
        translation_key="voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DuosidaSensorEntityDescription(
        key="power_active_import",
        translation_key="power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DuosidaSensorEntityDescription(
        key="energy_active_import_interval",
        translation_key="session_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DuosidaSensorEntityDescription(
        key="energy_active_import_register",
        translation_key="total_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    DuosidaSensorEntityDescription(
        key="frequency",
        translation_key="frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DuosidaSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DuosidaSensorEntityDescription(
        key="power_factor",
        translation_key="power_factor",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DuosidaSensorEntityDescription(
        key="connector_id",
        translation_key="connector_id",
    ),
    DuosidaSensorEntityDescription(
        key="transaction_id",
        translation_key="transaction_id",
    ),
    DuosidaSensorEntityDescription(
        key="vendor_transactionId",
        translation_key="vendor_transaction_id",
    ),
    DuosidaSensorEntityDescription(
        key="config_maxWorkCurrent",
        translation_key="configured_max_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DuosidaSensorEntityDescription(
        key="config_maxWorkVoltage",
        translation_key="configured_max_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DuosidaSensorEntityDescription(
        key="config_minWorkVoltage",
        translation_key="configured_min_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DuosidaSensorEntityDescription(
        key="config_maxWorkTemp",
        translation_key="configured_max_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DuosidaSensorEntityDescription(
        key="config_heartbeatInterval",
        translation_key="heartbeat_interval",
        native_unit_of_measurement="s",
    ),
    DuosidaSensorEntityDescription(
        key="config_meterValueSampleInterval",
        translation_key="meter_sample_interval",
        native_unit_of_measurement="s",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Duosida sensors."""
    coordinator: DuosidaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(DuosidaSensor(coordinator, description) for description in SENSORS)


class DuosidaSensor(DuosidaEntity, SensorEntity):
    """Duosida sensor entity."""

    entity_description: DuosidaSensorEntityDescription

    def __init__(
        self,
        coordinator: DuosidaDataUpdateCoordinator,
        description: DuosidaSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return sensor value."""
        value = self.value()
        if value in (None, ""):
            return None
        if self.entity_description.device_class is not None or self.entity_description.state_class is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        if isinstance(value, (str, int, float)):
            return value
        return str(value)
