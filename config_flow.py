"""Config flow for Emby integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EmbyAPIClient, EmbyAPIError, EmbyAuthError
from .const import CONF_API_KEY, DEFAULT_NAME, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_API_KEY): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)
    client = EmbyAPIClient(
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        api_key=data[CONF_API_KEY],
        session=session,
    )

    # Test the connection
    try:
        info = await client.get_system_info_public()
        if not info or "ServerName" not in info:
            raise EmbyAPIError("Invalid response from server")
    except EmbyAuthError as err:
        raise ValueError("authentication_failed") from err
    except EmbyAPIError as err:
        raise ValueError("cannot_connect") from err

    # Return info that you want to store in the config entry.
    return {
        "title": info.get("ServerName", DEFAULT_NAME),
        "server_id": info.get("Id"),
        "version": info.get("Version"),
    }


class EmbyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Emby."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except ValueError as err:
                error_str = str(err)
                if "authentication_failed" in error_str:
                    errors["base"] = "invalid_auth"
                elif "cannot_connect" in error_str:
                    errors["base"] = "cannot_connect"
                else:
                    errors["base"] = "unknown"
                _LOGGER.exception("Unexpected exception: %s", err)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Set unique ID to prevent duplicate entries
                await self.async_set_unique_id(info["server_id"])
                self._abort_if_unique_id_configured()

                # Create entry directly without device selection
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EmbyOptionsFlowHandler:
        """Get the options flow for this handler."""
        return EmbyOptionsFlowHandler(config_entry)


class EmbyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Emby integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._devices = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return await self.async_step_device_management()

    async def async_step_device_management(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage monitored devices."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "add_device":
                return await self.async_step_add_device()
            elif action == "remove_device":
                return await self.async_step_remove_device()
            elif action == "done":
                return self.async_create_entry(title="", data=self.config_entry.options)

        # Get current monitored devices
        monitored_devices = self.config_entry.options.get("monitored_devices", [])

        # Build description of current devices
        if monitored_devices:
            device_list = "\n".join([
                f"• {d['device_name']} ({d['user_name']})"
                for d in monitored_devices
            ])
            description = f"当前监控的设备：\n{device_list}"
        else:
            description = "当前没有监控任何设备"

        return self.async_show_form(
            step_id="device_management",
            data_schema=vol.Schema({
                vol.Required("action", default="done"): vol.In({
                    "add_device": "添加监控设备",
                    "remove_device": "删除监控设备",
                    "done": "完成",
                }),
            }),
            description_placeholders={"description": description},
        )

    async def async_step_add_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a device to monitor."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input.get("device_id")
            if device_id:
                # Find selected device info
                selected_device = None
                for device in self._devices:
                    if device.get("device_id") == device_id:
                        selected_device = device
                        break

                if selected_device:
                    # Add to monitored devices
                    monitored_devices = list(self.config_entry.options.get("monitored_devices", []))

                    # Check if already monitored
                    already_exists = any(
                        d["device_id"] == device_id
                        for d in monitored_devices
                    )

                    if already_exists:
                        errors["base"] = "device_already_monitored"
                    else:
                        monitored_devices.append(selected_device)

                        # Update options
                        new_options = {**self.config_entry.options}
                        new_options["monitored_devices"] = monitored_devices

                        # Save and return to device management
                        self.hass.config_entries.async_update_entry(
                            self.config_entry,
                            options=new_options
                        )

                        return await self.async_step_device_management()

        # Fetch available devices
        try:
            session = async_get_clientsession(self.hass)
            client = EmbyAPIClient(
                host=self.config_entry.data[CONF_HOST],
                port=self.config_entry.data[CONF_PORT],
                api_key=self.config_entry.data[CONF_API_KEY],
                session=session,
            )
            devices_data = await client.get_devices()
            raw_devices = devices_data.get("Items", [])

            # Process devices
            self._devices = []
            monitored_device_ids = [
                d["device_id"]
                for d in self.config_entry.options.get("monitored_devices", [])
            ]

            for device in raw_devices:
                device_id = device.get("ReportedDeviceId") or device.get("Id")
                device_name = device.get("Name", "Unknown")
                last_user = device.get("LastUserName", "Unknown")
                app_name = device.get("AppName", "")

                # Skip already monitored devices
                if device_id in monitored_device_ids:
                    continue

                self._devices.append({
                    "device_id": device_id,
                    "device_name": device_name,
                    "user_name": last_user,
                    "app_name": app_name,
                })

        except Exception as err:
            _LOGGER.error("Failed to fetch devices: %s", err)
            errors["base"] = "cannot_connect"
            self._devices = []

        if not self._devices and not errors:
            # No more devices to add
            return await self.async_step_device_management()

        # Build device selection options
        device_options = {}
        for device in self._devices:
            display_name = device["device_name"]
            if device["app_name"]:
                display_name = f"{display_name} ({device['app_name']})"
            if device["user_name"]:
                display_name = f"{display_name} - {device['user_name']}"

            device_options[device["device_id"]] = display_name

        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema({
                vol.Required("device_id"): vol.In(device_options),
            }),
            errors=errors,
            description_placeholders={
                "devices_count": str(len(self._devices))
            },
        )

    async def async_step_remove_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove a monitored device."""
        monitored_devices = self.config_entry.options.get("monitored_devices", [])

        if not monitored_devices:
            return await self.async_step_device_management()

        if user_input is not None:
            device_id = user_input.get("device_id")
            if device_id:
                # Remove device from monitored list
                new_monitored = [
                    d for d in monitored_devices
                    if d["device_id"] != device_id
                ]

                # Update options
                new_options = {**self.config_entry.options}
                new_options["monitored_devices"] = new_monitored

                # Save and return to device management
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    options=new_options
                )

                return await self.async_step_device_management()

        # Build device selection for removal
        device_options = {}
        for device in monitored_devices:
            display_name = device["device_name"]
            if device.get("app_name"):
                display_name = f"{display_name} ({device['app_name']})"
            if device.get("user_name"):
                display_name = f"{display_name} - {device['user_name']}"

            device_options[device["device_id"]] = display_name

        return self.async_show_form(
            step_id="remove_device",
            data_schema=vol.Schema({
                vol.Required("device_id"): vol.In(device_options),
            }),
        )
