"""Unit tests for sensor value computation."""
from __future__ import annotations
from custom_components.panamax_bluebolt.const import PanamaxState


def _make_state(voltage: int = 120, current: int = 10) -> PanamaxState:
    return PanamaxState(
        outlets={n: True for n in range(1, 9)},
        voltage=voltage,
        current=current,
        power_ok=True,
        breaker_ok=True,
        wire_fault_ok=True,
        temperature_ok=True,
        avm_ok=True,
        reboot_delays={n: 30 for n in range(1, 9)},
    )


class TestVoltageReading:
    def test_voltage_value(self) -> None:
        state = _make_state(voltage=124)
        assert state.voltage == 124

    def test_zero_voltage(self) -> None:
        state = _make_state(voltage=0)
        assert state.voltage == 0


class TestCurrentReading:
    def test_current_value(self) -> None:
        state = _make_state(current=12)
        assert state.current == 12

    def test_zero_current(self) -> None:
        state = _make_state(current=0)
        assert state.current == 0


class TestApparentPowerComputation:
    def test_apparent_power(self) -> None:
        state = _make_state(voltage=120, current=10)
        assert state.voltage * state.current == 1200

    def test_real_device_values(self) -> None:
        state = _make_state(voltage=124, current=12)
        assert state.voltage * state.current == 1488

    def test_zero_current_gives_zero_power(self) -> None:
        state = _make_state(voltage=120, current=0)
        assert state.voltage * state.current == 0
