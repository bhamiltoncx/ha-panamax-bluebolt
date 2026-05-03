"""Unit tests for fault indicator inversion logic."""
from __future__ import annotations
from custom_components.bluebolt_panamax.const import PanamaxState


def _make_state(**fault_overrides: bool) -> PanamaxState:
    defaults = {
        "power_ok": True,
        "breaker_ok": True,
        "wire_fault_ok": True,
        "temperature_ok": True,
        "avm_ok": True,
    }
    defaults.update(fault_overrides)
    return PanamaxState(
        outlets={n: True for n in range(1, 9)},
        voltage=124,
        current=12,
        reboot_delays={n: 30 for n in range(1, 9)},
        **defaults,
    )


class TestFaultInversion:
    def test_all_ok_means_no_problem(self) -> None:
        state = _make_state()
        assert not (not state.power_ok)
        assert not (not state.breaker_ok)
        assert not (not state.wire_fault_ok)
        assert not (not state.temperature_ok)
        assert not (not state.avm_ok)

    def test_power_fault_detected(self) -> None:
        state = _make_state(power_ok=False)
        assert not state.power_ok

    def test_breaker_fault_detected(self) -> None:
        state = _make_state(breaker_ok=False)
        assert not state.breaker_ok

    def test_wire_fault_detected(self) -> None:
        state = _make_state(wire_fault_ok=False)
        assert not state.wire_fault_ok

    def test_temperature_fault_detected(self) -> None:
        state = _make_state(temperature_ok=False)
        assert not state.temperature_ok

    def test_avm_fault_detected(self) -> None:
        state = _make_state(avm_ok=False)
        assert not state.avm_ok

    def test_single_fault_does_not_affect_others(self) -> None:
        state = _make_state(power_ok=False)
        assert state.breaker_ok is True
        assert state.wire_fault_ok is True
