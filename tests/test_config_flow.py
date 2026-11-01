"""Tests for the config flow."""

from __future__ import annotations

from unittest.mock import MagicMock

from pyezvizapi.exceptions import EzvizAuthVerificationCode, InvalidURL, PyEzvizError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ezviz_smart_plug.const import DOMAIN

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import TOKEN, USERNAME

USER_INPUT = {
    CONF_USERNAME: USERNAME,
    CONF_PASSWORD: "secret",
    CONF_URL: "apiieu.ezvizlife.com",
}


async def _start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow_success(hass: HomeAssistant, mock_client: MagicMock) -> None:
    """The account is added and the password is not stored."""
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == USERNAME
    assert result["data"] == {
        CONF_USERNAME: USERNAME,
        "session_id": TOKEN["session_id"],
        "rf_session_id": TOKEN["rf_session_id"],
        CONF_URL: TOKEN["api_url"],
    }
    assert CONF_PASSWORD not in result["data"]


async def test_user_flow_errors_then_success(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """Errors are shown and the flow can recover."""
    result = await _start(hass)

    mock_client.login.side_effect = PyEzvizError("bad")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    mock_client.login.side_effect = InvalidURL("bad url")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"] == {"base": "invalid_host"}

    mock_client.login.side_effect = None
    mock_client.login.return_value = dict(TOKEN)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_mfa(hass: HomeAssistant, mock_client: MagicMock) -> None:
    """The verification code step finishes the login."""
    result = await _start(hass)

    mock_client.login.side_effect = EzvizAuthVerificationCode("mfa")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "mfa"

    # wrong code
    mock_client.login.side_effect = PyEzvizError("The MFA code is invalid")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"code": "123456"}
    )
    assert result["errors"] == {"base": "invalid_code"}

    # right code
    mock_client.login.side_effect = None
    mock_client.login.return_value = dict(TOKEN)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"code": "654321"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    mock_client.login.assert_called_with(654321)


async def test_already_configured(
    hass: HomeAssistant, mock_client: MagicMock, config_entry: MockConfigEntry
) -> None:
    """The same account cannot be added twice."""
    config_entry.add_to_hass(hass)
    result = await _start(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(
    hass: HomeAssistant, mock_client: MagicMock, config_entry: MockConfigEntry
) -> None:
    """Re-authentication asks for the password and updates the entry."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    mock_client.login.return_value = {**TOKEN, "session_id": "new", "rf_session_id": "newrf"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "secret"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data["session_id"] == "new"
    assert config_entry.data["rf_session_id"] == "newrf"
