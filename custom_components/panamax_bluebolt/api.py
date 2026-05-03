"""Stateless async telnet client for Panamax BlueBOLT PDUs."""
from __future__ import annotations
import asyncio
import logging
from .const import (
    TELNET_READ_TIMEOUT,
    parse_fault_status,
    parse_int_value,
    parse_list_config,
    parse_outlet_status,
)

_LOGGER = logging.getLogger(__name__)


class PanamaxConnectionError(Exception):
    """Raised when unable to connect to or communicate with the device."""


async def _send_command(host: str, port: int, command: str, lines_expected: int = 1) -> str:
    """Open a connection, send one command, read response, close."""
    result_lines = []
    try:
        async with asyncio.timeout(TELNET_READ_TIMEOUT):
            reader, writer = await asyncio.open_connection(host, port)
            result_lines = []
            try:
                writer.write((command + "\r\n").encode())
                await writer.drain()
                line_num = 0
                while lines_expected < 0 or line_num < lines_expected:
                    data = await reader.readuntil(b'\r\n')
                    result_lines.append(data.decode(errors="replace"))
                    line_num += 1
            finally:
                writer.close()
                await writer.wait_closed()
    except TimeoutError as exc:
        if lines_expected >= 0:
            raise PanamaxConnectionError(
                f"Cannot connect to {host}:{port}: {exc}"
            ) from exc
    except OSError as exc:
        raise PanamaxConnectionError(
            f"Cannot connect to {host}:{port}: {exc}"
        ) from exc
    return ''.join(result_lines)



class PanamaxClient:
    """Stateless async telnet client — one method per device command."""

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port

    async def get_id(self) -> str:
        """Return the raw ?ID response (model and firmware lines)."""
        return await _send_command(self._host, self._port, "?ID", lines_expected=3)

    async def get_outlet_status(self) -> dict[int, bool]:
        """Return {outlet_number: is_on} for all 8 outlets."""
        raw = await _send_command(self._host, self._port, "?OUTLETSTAT", lines_expected=8)
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

    async def get_config(self) -> dict[str, str]:
        """Return configuration dictionary (from ?LIST_CONFIG)."""
        raw = await _send_command(self._host, self._port, "?LIST_CONFIG", lines_expected=-1)
        return parse_list_config(raw)

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
