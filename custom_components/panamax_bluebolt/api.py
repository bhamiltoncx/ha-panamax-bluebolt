"""Stateless async telnet client for Panamax BlueBOLT PDUs."""
from __future__ import annotations
import asyncio
import logging
from .const import (
    FEEDBACK_INIT_TIMEOUT,
    TELNET_READ_TIMEOUT,
    PanamaxState,
    parse_fault_status,
    parse_feedback_dump,
    parse_int_value,
    parse_list_config,
    parse_outlet_status,
)

_LOGGER = logging.getLogger(__name__)


class _DeviceLog(logging.LoggerAdapter):
    """Logger adapter that prepends [host:port] to every message."""

    def process(self, msg: str, kwargs: object) -> tuple[str, object]:
        return f"[{self.extra['device']}] {msg}", kwargs


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


class FeedbackConnection:
    """Persistent TCP connection using !SET_FEEDBACK ON for push state updates."""

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._log = _DeviceLog(_LOGGER, {"device": f"{host}:{port}"})

    @property
    def is_connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def connect(self) -> PanamaxState:
        """Open connection, enable feedback, read initial state dump.

        Phase 1: wait (up to FEEDBACK_INIT_TIMEOUT) for the $FEEDBACK=ON ack.
        Phase 2: read any following state lines with a short per-line timeout.
                 Break immediately on timeout or on $FEEDBACK=ON after outlet data.

        Some devices send no state dump after the ack (one $FEEDBACK=ON total);
        others send a full dump ending with a second $FEEDBACK=ON. Both are handled.
        """
        self._log.debug("Connecting")
        reader: asyncio.StreamReader | None = None
        writer: asyncio.StreamWriter | None = None
        dump_lines: list[str] = []
        try:
            async with asyncio.timeout(FEEDBACK_INIT_TIMEOUT):
                reader, writer = await asyncio.open_connection(self._host, self._port)
                self._log.debug("TCP connection established, sending !SET_FEEDBACK ON")
                writer.write(b"!SET_FEEDBACK ON\r\n")
                await writer.drain()

                # Phase 1: wait for the !SET_FEEDBACK ON acknowledgment line.
                while True:
                    raw_line = await reader.readuntil(b"\r\n")
                    decoded = raw_line.decode(errors="replace").strip()
                    self._log.debug("Dump line: %r", decoded)
                    if decoded == "$FEEDBACK=ON":
                        break  # ack received
                    dump_lines.append(decoded)

            # Phase 2: read optional state dump with a short per-line timeout.
            # If the device sends no dump, the first wait_for times out and we
            # proceed with an empty initial state (push updates populate it later).
            saw_outlet_data = False
            while True:
                try:
                    raw_line = await asyncio.wait_for(
                        reader.readuntil(b"\r\n"), timeout=TELNET_READ_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    break  # no more data; use whatever dump_lines we have
                decoded = raw_line.decode(errors="replace").strip()
                self._log.debug("Dump line: %r", decoded)
                if decoded.lstrip("$").upper().startswith("OUTLET"):
                    saw_outlet_data = True
                if decoded == "$FEEDBACK=ON":
                    if saw_outlet_data:
                        break  # end-of-dump marker after state data
                    # extra $FEEDBACK=ON without state data — ignore and continue
                else:
                    dump_lines.append(decoded)

        except (OSError, TimeoutError) as exc:
            self._log.debug("Connection failed: %s", exc)
            if writer is not None:
                try:
                    writer.close()
                except OSError:
                    pass
            raise PanamaxConnectionError(
                f"Cannot connect to {self._host}:{self._port}: {exc}"
            ) from exc

        self._log.debug("Initial dump complete (%d lines)", len(dump_lines))
        self._reader = reader
        self._writer = writer
        return parse_feedback_dump(dump_lines)

    async def read_line(self) -> str:
        """Read one push notification line from the open stream."""
        if self._reader is None:
            raise PanamaxConnectionError("Not connected")
        raw_line = await self._reader.readuntil(b"\r\n")
        line = raw_line.decode(errors="replace").strip()
        self._log.debug("Push line: %r", line)
        return line

    async def send_command(self, command: str) -> None:
        """Write a command to the open connection. Does not read a response."""
        if self._writer is None or self._writer.is_closing():
            raise PanamaxConnectionError("Not connected")
        self._log.debug("Sending command: %r", command)
        self._writer.write((command + "\r\n").encode())
        await self._writer.drain()

    async def __aenter__(self) -> PanamaxState:
        return await self.connect()

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the connection cleanly."""
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except OSError:
                pass
            finally:
                self._writer = None
                self._reader = None
