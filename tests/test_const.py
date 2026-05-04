"""Unit tests for parse helpers in const.py."""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent / "custom_components" / "panamax_bluebolt"


def _load(name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_const = _load("custom_components.panamax_bluebolt.const", _ROOT / "const.py")

OUTLETSTAT_RAW = (
    "$OUTLET1 = ON\r\n$OUTLET2 = ON\r\n$OUTLET3 = OFF\r\n$OUTLET4 = ON\r\n"
    "$OUTLET5 = ON\r\n$OUTLET6 = ON\r\n$OUTLET7 = ON\r\n$OUTLET8 = ON\r\n"
)
VOLTAGE_RAW = "$VOLTAGE = 124\r\n"
CURRENT_RAW = "$CURRENT = 12\r\n"
FAULTSTAT_OK = (
    "$PWR = OK\r\n$BREAKER = OK\r\n$WIRE FAULT = OK\r\n"
    "$TEMPERATURE = OK\r\n$AVM = OK\r\n"
)
FAULTSTAT_FAULT = (
    "$PWR = FAULT\r\n$BREAKER = OK\r\n$WIRE FAULT = OK\r\n"
    "$TEMPERATURE = OK\r\n$AVM = OK\r\n"
)
LIST_CONFIG_RAW = (
    "$TRIGGER FOR OUTLET1 = BUTTON_1\r\n$TRIGGER FOR OUTLET1 = BUTTON_GREEN\r\n"
    "$DELAY FOR OUTLET1 = 1, 15\r\n$DELAY FOR OUTLET2 = 2, 14\r\n"
    "$DELAY FOR OUTLET3 = 3, 13\r\n$DELAY FOR OUTLET4 = 4, 12\r\n"
    "$DELAY FOR OUTLET5 = 5, 11\r\n$DELAY FOR OUTLET6 = 6, 10\r\n"
    "$DELAY FOR OUTLET7 = 7, 6\r\n$DELAY FOR OUTLET8 = 12, 1\r\n"
    "$FEEDBACK=ON\r\n$LINEFEED=ON\r\n$PROFILE = CUSTOM\r\n"
    "$REBOOT_DELAY1 = 30\r\n$REBOOT_DELAY2 = 30\r\n"
)


class TestParseOutletStatus:
    def test_all_on(self) -> None:
        raw = "$OUTLET1 = ON\r\n$OUTLET2 = ON\r\n"
        result = _const.parse_outlet_status(raw)  # type: ignore[attr-defined]
        assert result == {1: True, 2: True}

    def test_mixed_states(self) -> None:
        result = _const.parse_outlet_status(OUTLETSTAT_RAW)  # type: ignore[attr-defined]
        assert result[3] is False
        assert result[1] is True
        assert len(result) == 8

    def test_off_outlet(self) -> None:
        raw = "$OUTLET5 = OFF\r\n"
        result = _const.parse_outlet_status(raw)  # type: ignore[attr-defined]
        assert result == {5: False}

    def test_empty_string(self) -> None:
        result = _const.parse_outlet_status("")  # type: ignore[attr-defined]
        assert result == {}


class TestParseIntValue:
    def test_voltage(self) -> None:
        result = _const.parse_int_value(VOLTAGE_RAW, "VOLTAGE")  # type: ignore[attr-defined]
        assert result == 124

    def test_current(self) -> None:
        result = _const.parse_int_value(CURRENT_RAW, "CURRENT")  # type: ignore[attr-defined]
        assert result == 12

    def test_missing_key_returns_zero(self) -> None:
        result = _const.parse_int_value("$VOLTAGE = 124\r\n", "CURRENT")  # type: ignore[attr-defined]
        assert result == 0


class TestParseFaultStatus:
    def test_all_ok(self) -> None:
        result = _const.parse_fault_status(FAULTSTAT_OK)  # type: ignore[attr-defined]
        assert result == {
            "power_ok": True,
            "breaker_ok": True,
            "wire_fault_ok": True,
            "temperature_ok": True,
            "avm_ok": True,
        }

    def test_power_fault(self) -> None:
        result = _const.parse_fault_status(FAULTSTAT_FAULT)  # type: ignore[attr-defined]
        assert result["power_ok"] is False
        assert result["breaker_ok"] is True

    def test_empty_string_defaults_ok(self) -> None:
        result = _const.parse_fault_status("")  # type: ignore[attr-defined]
        assert all(v is True for v in result.values())


class TestParseRebootDelays:
    def test_all_eight_outlets(self) -> None:
        config = _const.parse_list_config(LIST_CONFIG_RAW)
        result = _const.parse_reboot_delays(config)
        assert len(result) == 8

    def test_outlet1_off_delay(self) -> None:
        config = _const.parse_list_config(LIST_CONFIG_RAW)
        result = _const.parse_reboot_delays(config)
        assert result[1] == 15

    def test_outlet8_off_delay(self) -> None:
        config = _const.parse_list_config(LIST_CONFIG_RAW)
        result = _const.parse_reboot_delays(config)
        assert result[8] == 1

    def test_skips_trigger_lines(self) -> None:
        config = _const.parse_list_config(LIST_CONFIG_RAW)
        result = _const.parse_reboot_delays(config)
        assert all(isinstance(v, int) for v in result.values())


FEEDBACK_DUMP_LINES = [
    "$TRIGIN = ON",
    "$GREEN MODE = OFF",
    "$OUTLET1 = ON",
    "$OUTLET2 = ON",
    "$OUTLET3 = OFF",
    "$OUTLET4 = ON",
    "$OUTLET5 = ON",
    "$OUTLET6 = ON",
    "$OUTLET7 = ON",
    "$OUTLET8 = ON",
    "$VOLTAGE = 120",
    "$CURRENT = 18",
    "$PWR = OK",
    "$BREAKER = OK",
    "$WIRE FAULT = OK",
    "$TEMPERATURE = OK",
    "$AVM = OK",
    "$TRIGGER FOR OUTLET1 = BUTTON_1",
    "$TRIGGER FOR OUTLET1 = BUTTON_GREEN",
    "$DELAY FOR OUTLET1 = 1, 15",
    "$DELAY FOR OUTLET2 = 2, 14",
    "$DELAY FOR OUTLET3 = 3, 13",
    "$DELAY FOR OUTLET4 = 4, 12",
    "$DELAY FOR OUTLET5 = 5, 11",
    "$DELAY FOR OUTLET6 = 6, 10",
    "$DELAY FOR OUTLET7 = 7, 6",
    "$DELAY FOR OUTLET8 = 12, 1",
]


class TestParseFeedbackDump:
    def test_outlets_parsed(self) -> None:
        state = _const.parse_feedback_dump(FEEDBACK_DUMP_LINES)  # type: ignore[attr-defined]
        assert state.outlets == {1: True, 2: True, 3: False, 4: True, 5: True, 6: True, 7: True, 8: True}

    def test_power_sensors(self) -> None:
        state = _const.parse_feedback_dump(FEEDBACK_DUMP_LINES)  # type: ignore[attr-defined]
        assert state.voltage == 120
        assert state.current == 18

    def test_fault_status(self) -> None:
        state = _const.parse_feedback_dump(FEEDBACK_DUMP_LINES)  # type: ignore[attr-defined]
        assert state.power_ok is True
        assert state.breaker_ok is True
        assert state.wire_fault_ok is True
        assert state.temperature_ok is True
        assert state.avm_ok is True

    def test_reboot_delays(self) -> None:
        state = _const.parse_feedback_dump(FEEDBACK_DUMP_LINES)  # type: ignore[attr-defined]
        assert state.reboot_delays[1] == 15
        assert state.reboot_delays[8] == 1

    def test_ignores_unknown_lines(self) -> None:
        lines = FEEDBACK_DUMP_LINES + ["$FEEDBACK=ON", "$LINEFEED=ON", "$PROFILE = CUSTOM"]
        state = _const.parse_feedback_dump(lines)  # type: ignore[attr-defined]
        assert state.voltage == 120


class TestApplyFeedbackLine:
    def _base_state(self) -> object:
        return _const.parse_feedback_dump(FEEDBACK_DUMP_LINES)  # type: ignore[attr-defined]

    def test_outlet_on(self) -> None:
        state = self._base_state()
        new_state = _const.apply_feedback_line(state, "$OUTLET3 = ON")  # type: ignore[attr-defined]
        assert new_state is not None
        assert new_state.outlets[3] is True

    def test_outlet_off(self) -> None:
        state = self._base_state()
        new_state = _const.apply_feedback_line(state, "$OUTLET1 = OFF")  # type: ignore[attr-defined]
        assert new_state is not None
        assert new_state.outlets[1] is False

    def test_voltage_update(self) -> None:
        state = self._base_state()
        new_state = _const.apply_feedback_line(state, "$VOLTAGE = 119")  # type: ignore[attr-defined]
        assert new_state is not None
        assert new_state.voltage == 119

    def test_current_update(self) -> None:
        state = self._base_state()
        new_state = _const.apply_feedback_line(state, "$CURRENT = 20")  # type: ignore[attr-defined]
        assert new_state is not None
        assert new_state.current == 20

    def test_power_fault(self) -> None:
        state = self._base_state()
        new_state = _const.apply_feedback_line(state, "$PWR = FAULT")  # type: ignore[attr-defined]
        assert new_state is not None
        assert new_state.power_ok is False

    def test_wire_fault(self) -> None:
        state = self._base_state()
        new_state = _const.apply_feedback_line(state, "$WIRE FAULT = FAULT")  # type: ignore[attr-defined]
        assert new_state is not None
        assert new_state.wire_fault_ok is False

    def test_unknown_line_returns_none(self) -> None:
        state = self._base_state()
        assert _const.apply_feedback_line(state, "$FEEDBACK=ON") is None  # type: ignore[attr-defined]
        assert _const.apply_feedback_line(state, "$TRIGIN = ON") is None  # type: ignore[attr-defined]
        assert _const.apply_feedback_line(state, "$GREEN MODE = OFF") is None  # type: ignore[attr-defined]

    def test_original_state_unchanged(self) -> None:
        state = self._base_state()
        _const.apply_feedback_line(state, "$OUTLET1 = OFF")  # type: ignore[attr-defined]
        assert state.outlets[1] is True  # type: ignore[union-attr]
