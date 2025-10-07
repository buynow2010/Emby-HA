"""Binary sensor platform for Emby integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BINARY_SENSOR_TYPE_ACTIVE_STREAMS,
    BINARY_SENSOR_TYPE_IN_NETWORK,
    BINARY_SENSOR_TYPE_LIBRARY_SCANNING,
    BINARY_SENSOR_TYPE_ONLINE,
    BINARY_SENSOR_TYPE_PENDING_RESTART,
    BINARY_SENSOR_TYPE_TASKS_RUNNING,
    DOMAIN,
    ICON_FOLDER,
    ICON_NETWORK,
    ICON_ONLINE,
    ICON_PLAY,
    ICON_RESTART,
    ICON_TASK,
    INTEGRATION_VERSION,
    TASK_STATE_RUNNING,
)
from .sensor import EmbyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby binary sensor entries."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    binary_sensors = [
        # ===== 方案2：平衡方案（2个二进制传感器）=====
        EmbyOnlineBinarySensor(coordinator, entry),
        EmbyActiveStreamsBinarySensor(coordinator, entry),

        # ===== 已移除的二进制传感器 =====
        # EmbyLibraryScanningBinarySensor(coordinator, entry),
        # EmbyTasksRunningBinarySensor(coordinator, entry),
        # EmbyPendingRestartBinarySensor(coordinator, entry),
        # EmbyInNetworkBinarySensor(coordinator, entry),
    ]

    async_add_entities(binary_sensors)


class EmbyBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for Emby binary sensors."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.sensor_type = sensor_type
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"

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


class EmbyOnlineBinarySensor(EmbyBinarySensorBase):
    """Emby server online binary sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, BINARY_SENSOR_TYPE_ONLINE)
        self._attr_name = "Emby 在线"
        self._attr_icon = ICON_ONLINE
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool:
        """Return true if server is online."""
        system_info = self.coordinator.data.get("system_info", {})
        return bool(system_info.get("ServerName"))

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return True  # Always show online status


class EmbyActiveStreamsBinarySensor(EmbyBinarySensorBase):
    """Emby active streams binary sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, BINARY_SENSOR_TYPE_ACTIVE_STREAMS)
        self._attr_name = "Emby 有活动播放"
        self._attr_icon = ICON_PLAY
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._device_filter = entry.data.get("device_id")

    def _should_include_session(self, session: dict[str, Any]) -> bool:
        """Check if session should be included based on device filter."""
        if not self._device_filter or self._device_filter == "all":
            return True

        # Match both DeviceId (ReportedDeviceId) and InternalDeviceId
        session_device_id = session.get("DeviceId")
        session_internal_id = str(session.get("InternalDeviceId", ""))

        return (
            session_device_id == self._device_filter or
            session_internal_id == self._device_filter
        )

    @property
    def is_on(self) -> bool:
        """Return true if there are active streams."""
        sessions = self.coordinator.data.get("sessions", [])
        # Check if any session matching device filter is playing content
        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                return True
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        sessions = self.coordinator.data.get("sessions", [])
        active_streams = []
        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                active_streams.append({
                    "client": session.get("Client"),
                    "device": session.get("DeviceName"),
                    "user": session.get("UserName"),
                    "content": now_playing.get("Name"),
                    "type": now_playing.get("Type"),
                })

        result = {"active_streams": active_streams}

        # Add device filter info
        if self._device_filter and self._device_filter != "all":
            result["device_filter"] = self._device_filter
            result["device_filter_enabled"] = True
        else:
            result["device_filter"] = "所有设备"
            result["device_filter_enabled"] = False

        return result


class EmbyTasksRunningBinarySensor(EmbyBinarySensorBase):
    """Emby tasks running binary sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, BINARY_SENSOR_TYPE_TASKS_RUNNING)
        self._attr_name = "Emby 任务运行中"
        self._attr_icon = ICON_TASK
        self._attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool:
        """Return true if any task is running."""
        scheduled_tasks = self.coordinator.data.get("scheduled_tasks", [])
        for task in scheduled_tasks:
            if task.get("State") == TASK_STATE_RUNNING:
                return True
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        scheduled_tasks = self.coordinator.data.get("scheduled_tasks", [])
        running_tasks = [
            {
                "name": task.get("Name"),
                "category": task.get("Category"),
            }
            for task in scheduled_tasks
            if task.get("State") == TASK_STATE_RUNNING
        ]
        return {"running_tasks": running_tasks}


class EmbyPendingRestartBinarySensor(EmbyBinarySensorBase):
    """Emby pending restart binary sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, BINARY_SENSOR_TYPE_PENDING_RESTART)
        self._attr_name = "Emby 待重启"
        self._attr_icon = ICON_RESTART
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return true if server has pending restart."""
        system_info = self.coordinator.data.get("system_info", {})
        return system_info.get("HasPendingRestart", False)


class EmbyInNetworkBinarySensor(EmbyBinarySensorBase):
    """Emby in network binary sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, BINARY_SENSOR_TYPE_IN_NETWORK)
        self._attr_name = "Emby 网络内连接"
        self._attr_icon = ICON_NETWORK
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool:
        """Return true if connection is from within network."""
        endpoint_info = self.coordinator.data.get("endpoint_info", {})
        return endpoint_info.get("IsInNetwork", False)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        endpoint_info = self.coordinator.data.get("endpoint_info", {})
        return {
            "is_local": endpoint_info.get("IsLocal", False),
        }


class EmbyLibraryScanningBinarySensor(EmbyBinarySensorBase):
    """Emby library scanning binary sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, BINARY_SENSOR_TYPE_LIBRARY_SCANNING)
        self._attr_name = "Emby 正在扫描库"
        self._attr_icon = ICON_FOLDER
        self._attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool:
        """Return true if library is being scanned."""
        scheduled_tasks = self.coordinator.data.get("scheduled_tasks", [])
        
        # Check if any library scan task is running
        library_scan_keywords = ["库", "Library", "Scan", "扫描", "媒体库"]
        for task in scheduled_tasks:
            task_name = task.get("Name", "")
            task_state = task.get("State", "")
            
            # Check if it's a library-related task and it's running
            if task_state == TASK_STATE_RUNNING:
                if any(keyword in task_name for keyword in library_scan_keywords):
                    return True
        
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        scheduled_tasks = self.coordinator.data.get("scheduled_tasks", [])
        library_scan_keywords = ["库", "Library", "Scan", "扫描", "媒体库"]
        
        scanning_tasks = []
        for task in scheduled_tasks:
            task_name = task.get("Name", "")
            task_state = task.get("State", "")
            
            if task_state == TASK_STATE_RUNNING:
                if any(keyword in task_name for keyword in library_scan_keywords):
                    scanning_tasks.append({
                        "name": task_name,
                        "state": task_state,
                        "category": task.get("Category", ""),
                        "current_progress": task.get("CurrentProgressPercentage"),
                    })
        
        return {
            "scanning_tasks": scanning_tasks,
            "task_count": len(scanning_tasks),
        }
