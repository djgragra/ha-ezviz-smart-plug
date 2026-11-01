"""Switch platform for the EZVIZ Smart Plug integration."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from pyezvizapi.constants import DeviceSwitchType
from pyezvizapi.exceptions import PyEzvizError

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import EzvizPlug, EzvizSmartPlugConfigEntry, EzvizSmartPlugCoordinator

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzvizSmartPlugConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the plug switches, adding plugs that appear later."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new_plugs() -> None:
        new = set(coordinator.data) - known
        if not new:
            return
        known.update(new)
        async_add_entities(EzvizPlugSwitch(coordinator, serial) for serial in new)

    _add_new_plugs()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_plugs))


class EzvizPlugSwitch(CoordinatorEntity[EzvizSmartPlugCoordinator], SwitchEntity):
    """A single EZVIZ smart plug."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(self, coordinator: EzvizSmartPlugCoordinator, serial: str) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._serial = serial
        self._attr_unique_id = serial
        plug = coordinator.data[serial]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=plug.name,
            manufacturer=MANUFACTURER,
            model=plug.model,
            sw_version=plug.firmware,
            serial_number=serial,
        )

    @property
    def _plug(self) -> EzvizPlug | None:
        return self.coordinator.data.get(self._serial)

    @property
    def available(self) -> bool:
        """Return False when the plug is offline or no longer in the account."""
        plug = self._plug
        return super().available and plug is not None and plug.online

    @property
    def is_on(self) -> bool | None:
        """Return the plug state."""
        plug = self._plug
        return plug.is_on if plug is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the plug on."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the plug off."""
        await self._async_set(False)

    async def _async_set(self, enable: bool) -> None:
        client = self.coordinator.client
        try:
            await self.hass.async_add_executor_job(
                client.switch_status,
                self._serial,
                DeviceSwitchType.PLUG.value,
                enable,
            )
        except PyEzvizError as err:
            raise HomeAssistantError(
                f"Unable to switch {'on' if enable else 'off'} {self._serial}: {err}"
            ) from err

        plug = self._plug
        if plug is not None:
            self.coordinator.async_set_updated_data(
                {**self.coordinator.data, self._serial: replace(plug, is_on=enable)}
            )
