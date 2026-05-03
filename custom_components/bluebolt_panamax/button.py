"""Button platform for Panamax bulk and cycle controls."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import NUM_OUTLETS
from .coordinator import PanamaxCoordinator
from .helpers import panamax_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PanamaxCoordinator = entry.runtime_data
    entities: list[ButtonEntity] = [
        PanamaxAllOnButton(coordinator, entry),
        PanamaxAllOffButton(coordinator, entry),
    ]
    entities.extend(
        PanamaxCycleButton(coordinator, entry, n) for n in range(1, NUM_OUTLETS + 1)
    )
    async_add_entities(entities)


class PanamaxAllOnButton(CoordinatorEntity[PanamaxCoordinator], ButtonEntity):
    """Button to turn all outlets on simultaneously."""

    _attr_has_entity_name = True
    _attr_translation_key = "all_on"

    def __init__(self, coordinator: PanamaxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_all_on"
        self._attr_device_info = panamax_device_info(entry)

    async def async_press(self) -> None:
        await self.coordinator.client.all_on()
        await self.coordinator.async_request_refresh()


class PanamaxAllOffButton(CoordinatorEntity[PanamaxCoordinator], ButtonEntity):
    """Button to turn all outlets off simultaneously."""

    _attr_has_entity_name = True
    _attr_translation_key = "all_off"

    def __init__(self, coordinator: PanamaxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_all_off"
        self._attr_device_info = panamax_device_info(entry)

    async def async_press(self) -> None:
        await self.coordinator.client.all_off()
        await self.coordinator.async_request_refresh()


class PanamaxCycleButton(CoordinatorEntity[PanamaxCoordinator], ButtonEntity):
    """Button to power-cycle one outlet using its configured off-duration."""

    _attr_has_entity_name = True
    _attr_translation_key = "cycle_outlet"

    def __init__(
        self, coordinator: PanamaxCoordinator, entry: ConfigEntry, outlet: int
    ) -> None:
        super().__init__(coordinator)
        self._outlet = outlet
        self._attr_unique_id = f"{entry.entry_id}_cycle_{outlet}"
        self._attr_name = f"Cycle Outlet {outlet}"
        self._attr_device_info = panamax_device_info(entry)

    async def async_press(self) -> None:
        delay = self.coordinator.data.reboot_delays.get(self._outlet, 30)
        await self.coordinator.client.cycle_outlet(self._outlet, delay)
