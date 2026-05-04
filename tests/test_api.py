"""Integration tests for PanamaxClient — hit the real device.

Skip when BLUEBOLT_HOST environment variable is not set.
"""
from __future__ import annotations
import importlib.util
import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent / "custom_components" / "panamax_bluebolt"


def _load(name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_const_mod = _load("custom_components.panamax_bluebolt.const", _ROOT / "const.py")
_api = _load("custom_components.panamax_bluebolt.api", _ROOT / "api.py")

HOST = os.environ.get("BLUEBOLT_HOST", "")
PORT = int(os.environ.get("BLUEBOLT_PORT", "23"))

pytestmark = pytest.mark.skipif(
    not HOST,
    reason="BLUEBOLT_HOST not set",
)

PanamaxClient = _api.PanamaxClient  # type: ignore[attr-defined]
FeedbackConnection = _api.FeedbackConnection  # type: ignore[attr-defined]
PanamaxState = _const_mod.PanamaxState  # type: ignore[attr-defined]


@pytest.fixture()
def client() -> object:
    return PanamaxClient(HOST, PORT)


async def test_get_id(client: object) -> None:
    result = await client.get_id()  # type: ignore[union-attr]
    assert isinstance(result, str)
    assert "PANAMAX" in result.upper()


async def test_get_outlet_status(client: object) -> None:
    result = await client.get_outlet_status()  # type: ignore[union-attr]
    assert isinstance(result, dict)
    assert len(result) == 8
    assert all(isinstance(v, bool) for v in result.values())
    assert set(result.keys()) == set(range(1, 9))


async def test_get_voltage(client: object) -> None:
    result = await client.get_voltage()  # type: ignore[union-attr]
    assert isinstance(result, int)
    assert result > 0


async def test_get_current(client: object) -> None:
    result = await client.get_current()  # type: ignore[union-attr]
    assert isinstance(result, int)
    assert result >= 0


async def test_get_fault_status(client: object) -> None:
    result = await client.get_fault_status()  # type: ignore[union-attr]
    assert isinstance(result, dict)
    assert set(result.keys()) == {
        "power_ok", "breaker_ok", "wire_fault_ok", "temperature_ok", "avm_ok"
    }
    assert all(isinstance(v, bool) for v in result.values())


async def test_get_config(client: object) -> None:
    result = await client.get_config()
    assert isinstance(result, dict)
    assert all(isinstance(v, str) for v in result.keys())
    assert all(isinstance(v, str) for v in result.values())


@pytest.fixture()
def feedback_conn() -> object:
    return FeedbackConnection(HOST, PORT)


async def test_feedback_connect_returns_state(feedback_conn: object) -> None:
    async with feedback_conn as state:  # type: ignore[attr-defined]
        assert isinstance(state, PanamaxState)
        assert len(state.outlets) == 8
        assert all(isinstance(v, bool) for v in state.outlets.values())
        assert state.voltage > 0
        assert state.current >= 0
        assert len(state.reboot_delays) == 8


async def test_feedback_is_connected(feedback_conn: object) -> None:
    conn = feedback_conn
    assert not conn.is_connected  # type: ignore[union-attr]
    async with conn:  # type: ignore[attr-defined]
        assert conn.is_connected  # type: ignore[union-attr]
    assert not conn.is_connected  # type: ignore[union-attr]
