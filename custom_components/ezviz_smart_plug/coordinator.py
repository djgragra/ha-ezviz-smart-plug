"""DataUpdateCoordinator for the EZVIZ Smart Plug integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Any

from pyezvizapi.client import EzvizClient
from pyezvizapi.constants import DeviceCatagories, DeviceSwitchType
from pyezvizapi.exceptions import (
    EzvizAuthTokenExpired,
    EzvizAuthVerificationCode,
    HTTPError,
    InvalidURL,
    PyEzvizError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_RFSESSION_ID,
    CONF_SESSION_ID,
    DOMAIN,
    STATUS_OFFLINE,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type EzvizSmartPlugConfigEntry = ConfigEntry[EzvizSmartPlugCoordinator]


@dataclass(frozen=True, slots=True)
class EzvizPlug:
    """State of a smart plug as reported by the EZVIZ cloud."""

    serial: str
    name: str
    model: str | None
    firmware: str | None
    mac: str | None
    online: bool
    is_on: bool | None


def parse_plugs(records: dict[str, Any]) -> dict[str, EzvizPlug]:
    """Build plug states from pyezvizapi device records.

    Plugs are recognised by the device *category* reported by the cloud, not by
    the serial number prefix, so every plug model is picked up.
    """
    plugs: dict[str, EzvizPlug] = {}
    for serial, record in records.items():
        if getattr(record, "device_category", None) != DeviceCatagories.SOCKET.value:
            continue
        info = (record.raw or {}).get("deviceInfos") or {}
        switches = record.switches or {}
        plugs[serial] = EzvizPlug(
            serial=serial,
            name=record.name or serial,
            model=info.get("deviceType"),
            firmware=record.version,
            mac=info.get("mac"),
            online=record.status != STATUS_OFFLINE,
            is_on=switches.get(DeviceSwitchType.PLUG.value),
        )
    return plugs


def _fetch_plugs(client: EzvizClient) -> dict[str, EzvizPlug]:
    """Fetch the plugs (blocking, run in the executor)."""
    return parse_plugs(client.get_device_records(None))


class EzvizSmartPlugCoordinator(DataUpdateCoordinator[dict[str, EzvizPlug]]):
    """Fetch the plugs of an EZVIZ account."""

    config_entry: EzvizSmartPlugConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: EzvizSmartPlugConfigEntry,
        *,
        client: EzvizClient,
        timeout: int,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        self._timeout = timeout
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, EzvizPlug]:
        """Fetch data from the EZVIZ cloud."""
        try:
            async with asyncio.timeout(self._timeout):
                plugs = await self.hass.async_add_executor_job(_fetch_plugs, self.client)
        except (EzvizAuthTokenExpired, EzvizAuthVerificationCode) as err:
            raise ConfigEntryAuthFailed from err
        except (InvalidURL, HTTPError, PyEzvizError) as err:
            raise UpdateFailed(f"Invalid response from API: {err}") from err

        self._persist_token()
        return plugs

    def _persist_token(self) -> None:
        """Store the session tokens if the library renewed them."""
        # pyezvizapi keeps the current tokens in a private attribute; there is no
        # public accessor. Missing attribute simply means nothing to persist.
        token = getattr(self.client, "_token", None) or {}
        session_id = token.get("session_id")
        rf_session_id = token.get("rf_session_id")
        if not session_id or not rf_session_id:
            return
        data = self.config_entry.data
        if (
            data.get(CONF_SESSION_ID) == session_id
            and data.get(CONF_RFSESSION_ID) == rf_session_id
        ):
            return
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **data,
                CONF_SESSION_ID: session_id,
                CONF_RFSESSION_ID: rf_session_id,
            },
        )
