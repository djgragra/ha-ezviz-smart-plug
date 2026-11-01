"""Fixtures for the EZVIZ Smart Plug tests."""

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import CONF_URL, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ezviz_smart_plug.const import (
    CONF_RFSESSION_ID,
    CONF_SESSION_ID,
    DOMAIN,
)

USERNAME = "user@example.com"
SERIAL = "Q07320129"
TOKEN = {
    "session_id": "sess",
    "rf_session_id": "rfsess",
    "api_url": "apiieu.ezvizlife.com",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of the custom integration."""


def make_record(
    serial: str = SERIAL,
    *,
    category: str = "Socket",
    status: int = 1,
    is_on: bool | None = True,
    name: str = "Presa EZVIZ",
):
    """Build a fake pyezvizapi EzvizDeviceRecord."""
    return SimpleNamespace(
        serial=serial,
        name=name,
        device_category=category,
        version="V1.0.0",
        status=status,
        switches={14: is_on} if is_on is not None else {},
        raw={"deviceInfos": {"deviceType": "CS-T30-10A-EU", "mac": "AA:BB:CC:DD:EE:FF"}},
    )


@pytest.fixture
def records() -> dict:
    """Device records returned by the cloud."""
    return {
        SERIAL: make_record(),
        "BE8092563": make_record("BE8092563", category="IPC", is_on=None, name="Camera"),
    }


@pytest.fixture
def mock_client(records) -> Generator[MagicMock]:
    """Patch EzvizClient where the integration uses it."""
    client = MagicMock()
    client.login.return_value = dict(TOKEN)
    client.get_device_records.return_value = records
    client.switch_status.return_value = True
    client._token = dict(TOKEN)
    with (
        patch("custom_components.ezviz_smart_plug.EzvizClient", return_value=client),
        patch("custom_components.ezviz_smart_plug.config_flow.EzvizClient", return_value=client),
    ):
        yield client


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A configured entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=USERNAME,
        title=USERNAME,
        data={
            CONF_USERNAME: USERNAME,
            CONF_SESSION_ID: TOKEN["session_id"],
            CONF_RFSESSION_ID: TOKEN["rf_session_id"],
            CONF_URL: TOKEN["api_url"],
        },
    )
