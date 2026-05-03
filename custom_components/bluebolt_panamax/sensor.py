"""Sensor platform for Panamax power monitoring."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfApparentPower, UnitOfElectricCurrent, UnitOfElectricPotential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import PanamaxCoordinator
from .helpers import panamax_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PanamaxCoordinator = entry.runtime_data
    async_add_entities(
        [
            PanamaxVoltageSensor(coordinator, entry),
            PanamaxCurrentSensor(coordinator, entry),
            PanamaxApparentPowerSensor(coordinator, entry),
        ]
    )


class PanamaxVoltageSensor(CoordinatorEntity[PanamaxCoordinator], SensorEntity):
    """AC voltage sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "voltage"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    def __init__(self, coordinator: PanamaxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_voltage"
        self._attr_device_info = panamax_device_info(entry)

    @property
    def native_value(self) -> int:
        return self.coordinator.data.voltage


class PanamaxCurrentSensor(CoordinatorEntity[PanamaxCoordinator], SensorEntity):
    """Total current draw sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "current"
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    def __init__(self, coordinator: PanamaxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_current"
        self._attr_device_info = panamax_device_info(entry)

    @property
    def native_value(self) -> int:
        return self.coordinator.data.current


class PanamaxApparentPowerSensor(CoordinatorEntity[PanamaxCoordinator], SensorEntity):
    """Apparent power sensor computed as voltage × current."""

    _attr_has_entity_name = True
    _attr_translation_key = "apparent_power"
    _attr_device_class = SensorDeviceClass.APPARENT_POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfApparentPower.VOLT_AMPERE

    def __init__(self, coordinator: PanamaxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_apparent_power"
        self._attr_device_info = panamax_device_info(entry)

    @property
    def native_value(self) -> int:
        return self.coordinator.data.voltage * self.coordinator.data.current
