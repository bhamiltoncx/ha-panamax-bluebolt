"""Unit tests for outlet on/off state mapping in switch.py."""
from __future__ import annotations
from custom_components.panamax_bluebolt.const import PanamaxState


def _make_state(outlets: dict[int, bool]) -> PanamaxState:
    return PanamaxState(
        outlets=outlets,
        voltage=124,
        current=12,
        power_ok=True,
        breaker_ok=True,
        wire_fault_ok=True,
        temperature_ok=True,
        avm_ok=True,
        reboot_delays={n: 30 for n in range(1, 9)},
    )


class TestOutletStateMapping:
    def test_outlet_on(self) -> None:
        state = _make_state({1: True, 2: False})
        assert state.outlets[1] is True

    def test_outlet_off(self) -> None:
        state = _make_state({1: True, 2: False})
        assert state.outlets[2] is False

    def test_missing_outlet_returns_none(self) -> None:
        state = _make_state({})
        assert state.outlets.get(5) is None

    def test_all_eight_outlets_present(self) -> None:
        outlets = {n: True for n in range(1, 9)}
        state = _make_state(outlets)
        assert len(state.outlets) == 8
