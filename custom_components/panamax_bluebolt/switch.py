"""Switch platform for Panamax outlet control."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NUM_OUTLETS
from .coordinator import PanamaxCoordinator
from .helpers import panamax_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PanamaxCoordinator = entry.runtime_data
    async_add_entities(
        PanamaxOutletSwitch(coordinator, entry, n) for n in range(1, NUM_OUTLETS + 1)
    )


class PanamaxOutletSwitch(CoordinatorEntity[PanamaxCoordinator], SwitchEntity):
    """On/off control for one PDU outlet."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PanamaxCoordinator,
        entry: ConfigEntry,
        outlet: int,
    ) -> None:
        super().__init__(coordinator)
        self._outlet = outlet
        self._attr_unique_id = f"{entry.entry_id}_outlet_{outlet}"
        self._attr_name = f"Outlet {outlet}"
        self._attr_device_info = panamax_device_info(entry)

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.outlets.get(self._outlet)

    async def async_turn_on(self, **kwargs: object) -> None:
        await self.coordinator.send_command(f"!SWITCH {self._outlet} ON")

    async def async_turn_off(self, **kwargs: object) -> None:
        await self.coordinator.send_command(f"!SWITCH {self._outlet} OFF")
