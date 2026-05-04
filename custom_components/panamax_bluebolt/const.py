"""Constants and parse helpers for the Panamax BlueBOLT integration."""
from __future__ import annotations
from dataclasses import dataclass, replace as _dc_replace
from typing import Final

DOMAIN: Final = "panamax_bluebolt"

CONF_HOST: Final = "host"
CONF_PORT: Final = "port"

DEFAULT_PORT: Final = 23

TELNET_READ_TIMEOUT: Final = 2.0
FEEDBACK_INIT_TIMEOUT: Final = 60.0
NUM_OUTLETS: Final = 8


@dataclass
class PanamaxState:
    outlets: dict[int, bool]
    voltage: int
    current: int
    power_ok: bool
    breaker_ok: bool
    wire_fault_ok: bool
    temperature_ok: bool
    avm_ok: bool
    reboot_delays: dict[int, int]


def parse_outlet_status(raw: str) -> dict[int, bool]:
    """Parse ?OUTLETSTAT response: '$OUTLET1 = ON\r\n...' → {1: True, ...}"""
    result: dict[int, bool] = {}
    for line in raw.splitlines():
        line = line.strip().lstrip("$")
        if not line.upper().startswith("OUTLET"):
            continue
        try:
            key, val = line.split("=", 1)
            n = int(key.strip()[len("OUTLET"):])
            result[n] = val.strip().upper() == "ON"
        except (ValueError, IndexError):
            continue
    return result


def parse_int_value(raw: str, key: str) -> int:
    """Parse '$KEY = 124\r\n' → 124. Returns 0 if key not found."""
    for line in raw.splitlines():
        line = line.strip().lstrip("$")
        if line.upper().startswith(key.upper()):
            try:
                return int(line.split("=", 1)[1].strip())
            except (ValueError, IndexError):
                pass
    return 0


def parse_fault_status(raw: str) -> dict[str, bool]:
    """Parse ?FAULTSTAT response → {field: is_ok}. Defaults True if absent."""
    result: dict[str, bool] = {
        "power_ok": True,
        "breaker_ok": True,
        "wire_fault_ok": True,
        "temperature_ok": True,
        "avm_ok": True,
    }
    key_map = {
        "PWR": "power_ok",
        "BREAKER": "breaker_ok",
        "WIRE FAULT": "wire_fault_ok",
        "TEMPERATURE": "temperature_ok",
        "AVM": "avm_ok",
    }
    for line in raw.splitlines():
        line = line.strip().lstrip("$")
        for proto_key, field in key_map.items():
            if line.upper().startswith(proto_key):
                try:
                    val = line.split("=", 1)[1].strip().upper()
                    result[field] = val == "OK"
                except IndexError:
                    pass
    return result


def parse_list_config(raw: str) -> dict[str, str]:
    """Parse ?LIST_CONFIG → key-value dictionary."""
    result: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip().lstrip("$")
        if "=" not in line:
            continue
        left, right = line.split("=", 1)
        result[left] = right
    return result


def parse_reboot_delays(config: dict[str, str]) -> dict[int, int]:
    """Parse config dict → per-outlet off-duration in seconds.

    Config format: 'DELAY FOR OUTLET{n} -> {on_delay}, {off_delay}'
    Uses off_delay (second value) as the cycle delay.
    """
    result: dict[int, int] = {}
    for left, right in config.items():
        try:
            n = int(left.strip()[len("DELAY FOR OUTLET"):])
            delays = right.strip().split(",")
            result[n] = int(delays[-1].strip())
        except (ValueError, IndexError):
            continue
    return result


def parse_feedback_dump(lines: list[str]) -> PanamaxState:
    """Build a PanamaxState from the initial dump lines received before !SET_FEEDBACK ON."""
    raw = "\r\n".join(lines)
    config: dict[str, str] = {}
    for line in lines:
        line = line.strip().lstrip("$")
        if "=" not in line:
            continue
        left, right = line.split("=", 1)
        config[left] = right
    return PanamaxState(
        outlets=parse_outlet_status(raw),
        voltage=parse_int_value(raw, "VOLTAGE"),
        current=parse_int_value(raw, "CURRENT"),
        reboot_delays=parse_reboot_delays(config),
        **parse_fault_status(raw),
    )


_OUTLET_PREFIX = "OUTLET"
_FAULT_KEY_MAP: dict[str, str] = {
    "PWR": "power_ok",
    "BREAKER": "breaker_ok",
    "WIRE FAULT": "wire_fault_ok",
    "TEMPERATURE": "temperature_ok",
    "AVM": "avm_ok",
}


def apply_feedback_line(state: PanamaxState, line: str) -> PanamaxState | None:
    """Apply one push notification line to state. Returns new state or None if line is unknown."""
    line = line.strip().lstrip("$")
    if "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    key_upper = key.upper()

    if key_upper.startswith(_OUTLET_PREFIX):
        try:
            n = int(key_upper[len(_OUTLET_PREFIX):])
            new_outlets = dict(state.outlets)
            new_outlets[n] = value.upper() == "ON"
            return _dc_replace(state, outlets=new_outlets)
        except ValueError:
            return None

    if key_upper == "VOLTAGE":
        try:
            return _dc_replace(state, voltage=int(value))
        except ValueError:
            return None

    if key_upper == "CURRENT":
        try:
            return _dc_replace(state, current=int(value))
        except ValueError:
            return None

    for proto_key, field in _FAULT_KEY_MAP.items():
        if key_upper == proto_key:
            return _dc_replace(state, **{field: value.upper() == "OK"})

    return None
