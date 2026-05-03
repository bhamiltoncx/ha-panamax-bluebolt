"""Shared helpers used across all Panamax entity platforms."""
from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN


def panamax_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Build the single shared DeviceInfo for all Panamax entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Panamax",
        model=entry.data.get("model"),
        sw_version=entry.data.get("sw_version"),
    )
