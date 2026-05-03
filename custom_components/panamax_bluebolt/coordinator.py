"""DataUpdateCoordinator for the Panamax integration."""
from __future__ import annotations
import logging
import sys
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PanamaxClient, PanamaxConnectionError
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PanamaxState,
    parse_reboot_delays
)

_LOGGER = logging.getLogger(__name__)


class PanamaxCoordinator(DataUpdateCoordinator[PanamaxState]):
    """Polls all query commands and assembles PanamaxState on each interval."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        scan_interval = int(entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._client = PanamaxClient(
            entry.data[CONF_HOST],
            int(entry.data.get(CONF_PORT, DEFAULT_PORT)),
        )

    @property
    def client(self) -> PanamaxClient:
        """Expose the client for direct write calls from entity action handlers."""
        return self._client

    async def _async_update_data(self) -> PanamaxState:
        try:
            outlets = await self._client.get_outlet_status()
            voltage = await self._client.get_voltage()
            current = await self._client.get_current()
            faults = await self._client.get_fault_status()
            config = await self._client.get_config()
            delays = parse_reboot_delays(config)
        except PanamaxConnectionError as exc:
            raise UpdateFailed(str(exc)) from exc

        return PanamaxState(
            outlets=outlets,
            voltage=voltage,
            current=current,
            reboot_delays=delays,
            **faults,
        )
