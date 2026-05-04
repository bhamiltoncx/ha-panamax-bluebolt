"""DataUpdateCoordinator for the Panamax integration — push mode via !SET_FEEDBACK ON."""
from __future__ import annotations
import asyncio
import contextlib
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FeedbackConnection, PanamaxConnectionError
from .const import (
    CONF_HOST,
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
    PanamaxState,
    apply_feedback_line,
)

_LOGGER = logging.getLogger(__name__)

_RECONNECT_INITIAL = 5
_RECONNECT_MAX = 300


class _DeviceLog(logging.LoggerAdapter):
    """Logger adapter that prepends [host:port] to every message."""

    def process(self, msg: str, kwargs: object) -> tuple[str, object]:
        return f"[{self.extra['device']}] {msg}", kwargs


class PanamaxCoordinator(DataUpdateCoordinator[PanamaxState]):
    """Manages a persistent !SET_FEEDBACK ON connection and dispatches push updates."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self._conn = FeedbackConnection(
            host,
            port,
        )
        self._log = _DeviceLog(_LOGGER, {"device": f"{host}:{port}"})

    async def _async_setup(self) -> None:
        """Called once during setup by async_config_entry_first_refresh to set up the connection."""
        try:
            await self._conn.connect()
        except PanamaxConnectionError as exc:
            raise UpdateFailed(str(exc)) from exc

    async def _async_update_data(self) -> PanamaxState:
        """Called once by async_config_entry_first_refresh to establish the connection.

        HA may retry this after UpdateFailed; guard against spawning a second
        listener task on top of a still-running one.
        """
        state = await self._conn.get_initial_state()
        self._log.debug(f"Got initial state: {state}")
        # Tell the device to push delta updates directly to the socket.
        await self.send_command('!SET_FEEDBACK ON')
        return state

    def configure_tasks(self, entry: ConfigEntry) -> None:
        entry.async_create_background_task(
            self._run_listener(),
            name=f"{DOMAIN}_listener",
        )
        # TODO: Fetch power info occasionally

    async def _run_listener(self) -> None:
        """Background task: read push lines forever, reconnect on disconnect."""
        backoff = _RECONNECT_INITIAL
        while True:
            try:
                line = await self._conn.read_line()
                backoff = _RECONNECT_INITIAL
                new_state = apply_feedback_line(self.data, line)
                self._log.debug(f"Got pushed line: {line} Old state: {self.data} New state: {new_state}")
                if new_state is not None:
                    self.async_set_updated_data(new_state)
            except (OSError, asyncio.IncompleteReadError, PanamaxConnectionError) as exc:
                self._log.warning(
                    "Panamax feedback connection lost (%s). Reconnecting in %ds", exc, backoff
                )
                await self._conn.close()
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _RECONNECT_MAX)
                try:
                    await self._conn.connect()
                    new_state = await self._conn.get_initial_state()
                    self.async_set_updated_data(new_state)
                    backoff = _RECONNECT_INITIAL
                    self._log.info("Panamax feedback connection re-established")
                except (OSError, PanamaxConnectionError, TimeoutError) as reconnect_exc:
                    self._log.error("Panamax reconnect failed: %s", reconnect_exc)
            except asyncio.CancelledError:
                return

    async def send_command(self, command: str) -> None:
        """Send a write command on the feedback connection."""
        try:
            await self._conn.send_command(command)
        except PanamaxConnectionError as exc:
            self._log.error("Cannot send command %r: %s", command, exc)
