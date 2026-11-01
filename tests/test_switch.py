"""Tests for setup, coordinator parsing and the switch."""

from __future__ import annotations

from unittest.mock import MagicMock

from pyezvizapi.exceptions import EzvizAuthTokenExpired, PyEzvizError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ezviz_smart_plug.coordinator import parse_plugs

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .conftest import SERIAL, make_record

ENTITY_ID = "switch.presa_ezviz"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def test_parse_plugs_uses_category_not_serial_prefix() -> None:
    """Plugs with any serial are detected; cameras are ignored."""
    plugs = parse_plugs(
        {
            "Q123": make_record("Q123"),
            "X999": make_record("X999", status=2, is_on=False),
            "BE1": make_record("BE1", category="IPC", is_on=None),
        }
    )
    assert set(plugs) == {"Q123", "X999"}
    assert plugs["Q123"].is_on is True and plugs["Q123"].online is True
    assert plugs["X999"].is_on is False and plugs["X999"].online is False
    assert plugs["Q123"].model == "CS-T30-10A-EU"


async def test_setup_creates_only_the_plug(
    hass: HomeAssistant, mock_client: MagicMock, config_entry: MockConfigEntry
) -> None:
    """One switch per plug, none for cameras."""
    await _setup(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get(ENTITY_ID).state == STATE_ON
    assert len(hass.states.async_entity_ids("switch")) == 1


async def test_turn_off_and_on(
    hass: HomeAssistant, mock_client: MagicMock, config_entry: MockConfigEntry
) -> None:
    """Commands reach the cloud and the state updates."""
    await _setup(hass, config_entry)

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": ENTITY_ID}, blocking=True
    )
    mock_client.switch_status.assert_called_with(SERIAL, 14, False)
    assert hass.states.get(ENTITY_ID).state == STATE_OFF

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": ENTITY_ID}, blocking=True
    )
    mock_client.switch_status.assert_called_with(SERIAL, 14, True)
    assert hass.states.get(ENTITY_ID).state == STATE_ON


async def test_command_failure_raises(
    hass: HomeAssistant, mock_client: MagicMock, config_entry: MockConfigEntry
) -> None:
    """A cloud error surfaces as HomeAssistantError and keeps the state."""
    await _setup(hass, config_entry)
    mock_client.switch_status.side_effect = PyEzvizError("boom")

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch", "turn_off", {"entity_id": ENTITY_ID}, blocking=True
        )
    assert hass.states.get(ENTITY_ID).state == STATE_ON


async def test_offline_plug_is_unavailable(
    hass: HomeAssistant, mock_client: MagicMock, config_entry: MockConfigEntry, records
) -> None:
    """A plug reported offline by the cloud is unavailable."""
    records[SERIAL] = make_record(status=2)
    await _setup(hass, config_entry)

    assert hass.states.get(ENTITY_ID).state == STATE_UNAVAILABLE


async def test_expired_token_starts_reauth(
    hass: HomeAssistant, mock_client: MagicMock, config_entry: MockConfigEntry
) -> None:
    """An expired token puts the entry in setup error and starts reauth."""
    mock_client.login.side_effect = EzvizAuthTokenExpired("expired")
    await _setup(hass, config_entry)

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    assert any(
        flow["context"]["source"] == "reauth"
        for flow in hass.config_entries.flow.async_progress()
    )


async def test_cloud_error_retries_setup(
    hass: HomeAssistant, mock_client: MagicMock, config_entry: MockConfigEntry
) -> None:
    """A temporary cloud error does not remove the entry."""
    mock_client.login.side_effect = PyEzvizError("down")
    await _setup(hass, config_entry)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
