"""Diagnostics for the EZVIZ Smart Plug integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_RFSESSION_ID, CONF_SESSION_ID
from .coordinator import EzvizSmartPlugConfigEntry

TO_REDACT = {CONF_USERNAME, CONF_SESSION_ID, CONF_RFSESSION_ID, "serial", "mac"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EzvizSmartPlugConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "plugs": [
            async_redact_data(asdict(plug), TO_REDACT)
            for plug in entry.runtime_data.data.values()
        ],
    }
