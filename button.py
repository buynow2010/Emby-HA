"""Button platform for Emby integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BUTTON_TYPE_REFRESH,
    BUTTON_TYPE_TEST_CONNECTION,
    DOMAIN,
    ICON_CONNECTION,
    ICON_REFRESH,
    INTEGRATION_VERSION,
)
from .sensor import EmbyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby button entries."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]["client"]

    buttons = [
        # 移除不需要的按钮：
        # EmbyRefreshButton(coordinator, entry),
        # EmbyTestConnectionButton(coordinator, entry, client),
    ]

    async_add_entities(buttons)


class EmbyButtonBase(CoordinatorEntity, ButtonEntity):
    """Base class for Emby buttons."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
        button_type: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.entry = entry
        self.button_type = button_type
        self._attr_unique_id = f"{entry.entry_id}_{button_type}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        system_info = {}
        if self.coordinator.data:
            system_info = self.coordinator.data.get("system_info", {})
        server_name = system_info.get("ServerName", "Emby")
        server_id = system_info.get("Id", self.entry.entry_id)

        return {
            "identifiers": {(DOMAIN, server_id)},
            "name": server_name,
            "manufacturer": "buynow",
            "model": "Emby Server",
            "sw_version": system_info.get("Version", "Unknown"),
        }


class EmbyRefreshButton(EmbyButtonBase):
    """Emby refresh button."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, BUTTON_TYPE_REFRESH)
        self._attr_name = "Emby 刷新数据"
        self._attr_icon = ICON_REFRESH

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Refresh button pressed, updating data")
        await self.coordinator.async_request_refresh()


class EmbyTestConnectionButton(EmbyButtonBase):
    """Emby test connection button."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
        client,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, BUTTON_TYPE_TEST_CONNECTION)
        self._attr_name = "Emby 测试连接"
        self._attr_icon = ICON_CONNECTION
        self.client = client

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Test connection button pressed")
        success = await self.client.test_connection()
        if success:
            _LOGGER.info("Connection test successful")
        else:
            _LOGGER.error("Connection test failed")
