"""Config flow for the Panamax BlueBOLT integration."""
from __future__ import annotations
from typing import Any

import voluptuous as vol
from homeassistant.components import dhcp
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .api import PanamaxClient, PanamaxConnectionError
from .const import (
    CONF_HOST,
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
)


def _user_schema(default_host: str = "") -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=default_host): str,
            vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
                int, vol.Range(min=1, max=65535)
            ),
        }
    )


def _parse_id(raw: str) -> tuple[str, str]:
    """Return (model, firmware_version) from ?ID response."""
    lines = [
        line.strip().lstrip("$")
        for line in raw.splitlines()
        if line.strip().lstrip("$")
    ]
    model = ""
    fw = ""
    for line in lines:
        if line.upper().startswith("FIRMWARE"):
            fw = line.split(":", 1)[-1].strip()
        elif not line.upper().startswith("PANAMAX"):
            model = line
    return model or "PDU", fw


class PanamaxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle setup of a Panamax PDU."""

    VERSION = 1

    async def _try_connect(self, host: str, port: int) -> str | None:
        """Return raw ?ID string on success, None if connection fails."""
        try:
            client = PanamaxClient(host, port)
            return await client.get_id()
        except PanamaxConnectionError:
            return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host: str = user_input[CONF_HOST]
            port: int = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            raw_id = await self._try_connect(host, port)
            if raw_id is None:
                errors["base"] = "cannot_connect"
            else:
                model, fw = _parse_id(raw_id)
                uid = f"{model}_{host}"
                await self.async_set_unique_id(uid)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Panamax {model}",
                    data={
                        **user_input,
                        "model": model,
                        "sw_version": fw,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(self._discovered_host),
            errors=errors,
        )

    async def async_step_dhcp(
        self, discovery_info: dhcp.DhcpServiceInfo
    ) -> ConfigFlowResult:
        host = discovery_info.ip
        raw_id = await self._try_connect(host, DEFAULT_PORT)
        if raw_id is None:
            return self.async_abort(reason="cannot_connect")

        model, fw = _parse_id(raw_id)
        uid = f"{model}_{host}"
        await self.async_set_unique_id(uid)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Panamax {model}",
            data={
                CONF_HOST: host,
                CONF_PORT: DEFAULT_PORT,
                "model": model,
                "sw_version": fw,
            },
        )
