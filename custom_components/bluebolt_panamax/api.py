"""Stateless async telnet client for Panamax/BlueBolt PDUs."""
from __future__ import annotations
import asyncio
import logging
from .const import (
    TELNET_READ_TIMEOUT,
    parse_fault_status,
    parse_int_value,
    parse_outlet_status,
    parse_reboot_delays,
)

_LOGGER = logging.getLogger(__name__)


class PanamaxConnectionError(Exception):
    """Raised when unable to connect to or communicate with the device."""


async def _send_command(host: str, port: int, command: str) -> str:
    """Open a connection, send one command, read response until timeout, close."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=TELNET_READ_TIMEOUT,
        )
    except (OSError, asyncio.TimeoutError) as exc:
        raise PanamaxConnectionError(
            f"Cannot connect to {host}:{port}: {exc}"
        ) from exc

    try:
        writer.write((command + "\r\n").encode())
        await writer.drain()

        chunks: list[bytes] = []
        try:
            while True:
                chunk = await asyncio.wait_for(
                    reader.read(4096), timeout=TELNET_READ_TIMEOUT
                )
                if not chunk:
                    break
                chunks.append(chunk)
        except asyncio.TimeoutError:
            pass

        return b"".join(chunks).decode(errors="replace")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass


class PanamaxClient:
    """Stateless async telnet client — one method per device command."""

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port

    async def get_id(self) -> str:
        """Return the raw ?ID response (model and firmware lines)."""
        return await _send_command(self._host, self._port, "?ID")

    async def get_outlet_status(self) -> dict[int, bool]:
        """Return {outlet_number: is_on} for all 8 outlets."""
        raw = await _send_command(self._host, self._port, "?OUTLETSTAT")
        return parse_outlet_status(raw)

    async def get_voltage(self) -> int:
        """Return AC voltage in volts."""
        raw = await _send_command(self._host, self._port, "?VOLTAGE")
        return parse_int_value(raw, "VOLTAGE")

    async def get_current(self) -> int:
        """Return total current draw in amps."""
        raw = await _send_command(self._host, self._port, "?CURRENT")
        return parse_int_value(raw, "CURRENT")

    async def get_fault_status(self) -> dict[str, bool]:
        """Return {field: is_ok} for all five fault indicators."""
        raw = await _send_command(self._host, self._port, "?FAULTSTAT")
        return parse_fault_status(raw)

    async def get_reboot_delays(self) -> dict[int, int]:
        """Return per-outlet off-duration in seconds (from ?LIST_CONFIG)."""
        raw = await _send_command(self._host, self._port, "?LIST_CONFIG")
        return parse_reboot_delays(raw)

    async def switch_outlet(self, outlet: int, on: bool) -> None:
        """Turn a single outlet on or off."""
        state = "ON" if on else "OFF"
        await _send_command(self._host, self._port, f"!SWITCH {outlet} {state}")

    async def all_on(self) -> None:
        """Turn all outlets on simultaneously."""
        await _send_command(self._host, self._port, "!ALL_ON")

    async def all_off(self) -> None:
        """Turn all outlets off simultaneously."""
        await _send_command(self._host, self._port, "!ALL_OFF")

    async def cycle_outlet(self, outlet: int, delay: int) -> None:
        """Power-cycle one outlet with the given off-duration in seconds."""
        await _send_command(self._host, self._port, f"#CYCLE {outlet}:{delay}")
