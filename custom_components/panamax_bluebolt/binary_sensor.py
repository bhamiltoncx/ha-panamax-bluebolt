"""Binary sensor platform for Panamax fault indicators."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import PanamaxState
from .coordinator import PanamaxCoordinator
from .helpers import panamax_device_info


@dataclass(frozen=True)
class FaultSensorDescription:
    key: str
    translation_key: str
    is_fault: Callable[[PanamaxState], bool]


_FAULT_SENSORS: list[FaultSensorDescription] = [
    FaultSensorDescription("power", "power", lambda s: not s.power_ok),
    FaultSensorDescription("breaker", "breaker", lambda s: not s.breaker_ok),
    FaultSensorDescription("wire_fault", "wire_fault", lambda s: not s.wire_fault_ok),
    FaultSensorDescription("temperature", "temperature", lambda s: not s.temperature_ok),
    FaultSensorDescription("avm", "avm", lambda s: not s.avm_ok),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PanamaxCoordinator = entry.runtime_data
    async_add_entities(
        PanamaxFaultSensor(coordinator, entry, desc) for desc in _FAULT_SENSORS
    )


class PanamaxFaultSensor(CoordinatorEntity[PanamaxCoordinator], BinarySensorEntity):
    """Binary sensor: True when a fault is present, False when OK."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: PanamaxCoordinator,
        entry: ConfigEntry,
        desc: FaultSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._desc = desc
        self._attr_unique_id = f"{entry.entry_id}_fault_{desc.key}"
        self._attr_translation_key = desc.translation_key
        self._attr_device_info = panamax_device_info(entry)

    @property
    def is_on(self) -> bool:
        return self._desc.is_fault(self.coordinator.data)
