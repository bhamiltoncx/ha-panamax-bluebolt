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


class PanamaxCoordinator(DataUpdateCoordinator[PanamaxState]):
    """Manages a persistent !SET_FEEDBACK ON connection and dispatches push updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self._conn = FeedbackConnection(
            entry.data[CONF_HOST],
            int(entry.data.get(CONF_PORT, DEFAULT_PORT)),
        )
        self._listener_task: asyncio.Task[None] | None = None

    async def _async_update_data(self) -> PanamaxState:
        """Called once by async_config_entry_first_refresh to establish the connection.

        HA may retry this after UpdateFailed; guard against spawning a second
        listener task on top of a still-running one.
        """
        if self._listener_task is not None and not self._listener_task.done():
            assert self.data is not None
            return self.data
        try:
            state = await self._conn.connect()
        except PanamaxConnectionError as exc:
            raise UpdateFailed(str(exc)) from exc
        self._listener_task = self.hass.async_create_background_task(
            self._run_listener(),
            name=f"{DOMAIN}_listener",
        )
        return state

    async def _run_listener(self) -> None:
        """Background task: read push lines forever, reconnect on disconnect."""
        backoff = _RECONNECT_INITIAL
        while True:
            try:
                line = await self._conn.read_line()
                backoff = _RECONNECT_INITIAL
                new_state = apply_feedback_line(self.data, line)
                if new_state is not None:
                    self.async_set_updated_data(new_state)
            except (OSError, asyncio.IncompleteReadError, PanamaxConnectionError) as exc:
                _LOGGER.warning(
                    "Panamax feedback connection lost (%s). Reconnecting in %ds", exc, backoff
                )
                await self._conn.close()
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _RECONNECT_MAX)
                try:
                    new_state = await self._conn.connect()
                    self.async_set_updated_data(new_state)
                    backoff = _RECONNECT_INITIAL
                    _LOGGER.info("Panamax feedback connection re-established")
                except (OSError, PanamaxConnectionError, TimeoutError) as reconnect_exc:
                    _LOGGER.error("Panamax reconnect failed: %s", reconnect_exc)
            except asyncio.CancelledError:
                return

    async def send_command(self, command: str) -> None:
        """Send a write command on the feedback connection."""
        try:
            await self._conn.send_command(command)
        except PanamaxConnectionError as exc:
            _LOGGER.error("Cannot send command %r: %s", command, exc)

    async def async_shutdown(self) -> None:
        """Cancel the listener task and close the connection on unload."""
        if self._listener_task is not None:
            self._listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener_task
        await self._conn.close()
