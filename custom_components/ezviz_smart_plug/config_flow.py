"""Config flow for the EZVIZ Smart Plug integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from pyezvizapi.client import EzvizClient
from pyezvizapi.exceptions import (
    EzvizAuthVerificationCode,
    HTTPError,
    InvalidHost,
    InvalidURL,
    PyEzvizError,
)

from .const import (
    CONF_RFSESSION_ID,
    CONF_SESSION_ID,
    DEFAULT_TIMEOUT,
    DOMAIN,
    EU_URL,
)

try:  # Home Assistant 2026.x ships "probatio" as the voluptuous replacement.
    import probatio as vol
except ImportError:  # pragma: no cover - older Home Assistant
    import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

CONF_CODE = "code"


class EzvizSmartPlugConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EZVIZ Smart Plug."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._username: str = ""
        self._password: str = ""
        self._url: str = EU_URL
        self._client: EzvizClient | None = None
        self._reauth = False

    # -- helpers ---------------------------------------------------------------

    async def _async_login(
        self, sms_code: int | None = None
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Log in and return (entry data, error key)."""
        if self._client is None or sms_code is None:
            self._client = EzvizClient(self._username, self._password, self._url, DEFAULT_TIMEOUT)
        client = self._client
        try:
            token = await self.hass.async_add_executor_job(client.login, sms_code)
        except EzvizAuthVerificationCode:
            return None, "mfa_required"
        except InvalidURL:
            return None, "invalid_host"
        except (InvalidHost, HTTPError):
            return None, "cannot_connect"
        except PyEzvizError:
            return None, "invalid_auth"
        return {
            CONF_USERNAME: self._username,
            CONF_SESSION_ID: token[CONF_SESSION_ID],
            CONF_RFSESSION_ID: token[CONF_RFSESSION_ID],
            CONF_URL: token["api_url"],
        }, None

    async def _async_finish(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Create the entry, or update it when re-authenticating."""
        if self._reauth:
            return self.async_update_reload_and_abort(self._get_reauth_entry(), data_updates=data)
        return self.async_create_entry(title=self._username, data=data)

    # -- steps -----------------------------------------------------------------

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME].strip()
            self._password = user_input[CONF_PASSWORD]
            self._url = user_input[CONF_URL].strip() or EU_URL
            await self.async_set_unique_id(self._username.lower())
            self._abort_if_unique_id_configured()

            try:
                data, error = await self._async_login()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception")
                return self.async_abort(reason="unknown")
            if data:
                return await self._async_finish(data)
            if error == "mfa_required":
                return await self.async_step_mfa()
            errors["base"] = error or "unknown"

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=self._username): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_URL, default=self._url): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_mfa(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the verification code sent by EZVIZ."""
        errors: dict[str, str] = {}

        if user_input is not None:
            code = user_input[CONF_CODE].strip()
            if not code.isdigit():
                errors["base"] = "invalid_code"
            else:
                try:
                    data, error = await self._async_login(int(code))
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Unexpected exception")
                    return self.async_abort(reason="unknown")
                if data:
                    return await self._async_finish(data)
                errors["base"] = "invalid_code" if error == "invalid_auth" else (error or "unknown")

        return self.async_show_form(
            step_id="mfa",
            data_schema=vol.Schema({vol.Required(CONF_CODE): str}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start re-authentication when the stored tokens expired."""
        self._reauth = True
        self._username = entry_data[CONF_USERNAME]
        self._url = entry_data.get(CONF_URL) or EU_URL
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the account password again."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._password = user_input[CONF_PASSWORD]
            try:
                data, error = await self._async_login()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception")
                return self.async_abort(reason="unknown")
            if data:
                return await self._async_finish(data)
            if error == "mfa_required":
                return await self.async_step_mfa()
            errors["base"] = error or "unknown"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={CONF_USERNAME: self._username},
            errors=errors,
        )
