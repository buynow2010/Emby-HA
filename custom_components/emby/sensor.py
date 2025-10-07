"""Sensor platform for Emby integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import EmbyAPIClient, EmbyAPIError
from .const import (
    ATTR_ACTIVITIES,
    ATTR_ALBUM_COUNT,
    ATTR_ARTIST_COUNT,
    ATTR_DEVICES,
    ATTR_EPISODE_COUNT,
    ATTR_FOLDERS,
    ATTR_GAME_COUNT,
    ATTR_MOVIE_COUNT,
    ATTR_OPERATING_SYSTEM,
    ATTR_SERIES_COUNT,
    ATTR_SERVER_ID,
    ATTR_SESSIONS,
    ATTR_SONG_COUNT,
    ATTR_TASKS,
    ATTR_USERS,
    ATTR_VERSION,
    DOMAIN,
    ICON_ACTIVITY,
    ICON_DEVICE,
    ICON_EPISODE,
    ICON_FOLDER,
    ICON_MOVIE,
    ICON_PLAY,
    ICON_SERVER,
    ICON_SESSION,
    ICON_TASK,
    ICON_TOTAL,
    ICON_TV,
    ICON_USERS,
    ICON_VERSION,
    INTEGRATION_VERSION,
    SENSOR_TYPE_ACTIVE_SESSIONS,
    SENSOR_TYPE_DEVICE_COUNT,
    SENSOR_TYPE_EPISODE_COUNT,
    SENSOR_TYPE_LIBRARY_FOLDERS,
    SENSOR_TYPE_MOVIE_COUNT,
    SENSOR_TYPE_RECENT_ACTIVITIES,
    SENSOR_TYPE_SCHEDULED_TASKS,
    SENSOR_TYPE_SERIES_COUNT,
    SENSOR_TYPE_SERVER_NAME,
    SENSOR_TYPE_TOTAL_ITEMS,
    SENSOR_TYPE_TOTAL_USERS,
    SENSOR_TYPE_VERSION,
    SENSOR_TYPE_NOW_PLAYING,
    SENSOR_TYPE_PLAYBACK_STATE,
    SENSOR_TYPE_MEDIA_TYPE,
    SENSOR_TYPE_MEDIA_TITLE,
    SENSOR_TYPE_PROGRESS_PERCENT,
    SENSOR_TYPE_PLAYBACK_POSITION,
    SENSOR_TYPE_PLAYBACK_REMAINING,
    SENSOR_TYPE_SUBTITLE_TRACK,
    SENSOR_TYPE_AUDIO_TRACK,
    SENSOR_TYPE_TODAY_PLAY_COUNT,
    SENSOR_TYPE_TODAY_WATCH_TIME,
    SENSOR_TYPE_RECENTLY_ADDED,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby sensor entries."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # ===== Server-level sensors (created once) =====
    server_sensors = [
        # Media library statistics
        EmbyMovieCountSensor(coordinator, entry),
        EmbySeriesCountSensor(coordinator, entry),
        EmbyEpisodeCountSensor(coordinator, entry),

        # Media library
        EmbyRecentlyAddedSensor(coordinator, entry),
    ]

    # ===== Device-level sensors (created for each monitored device) =====
    device_sensors = []
    monitored_devices = entry.options.get("monitored_devices", [])

    for device in monitored_devices:
        device_id = device["device_id"]
        device_name = device["device_name"]
        user_name = device.get("user_name", "")

        # Create sensors for this device
        device_sensors.extend([
            EmbyNowPlayingSensor(coordinator, entry, device_id, device_name, user_name),
            EmbyPlaybackStateSensor(coordinator, entry, device_id, device_name, user_name),
            EmbyProgressPercentSensor(coordinator, entry, device_id, device_name, user_name),
            EmbyPlaybackRemainingSensor(coordinator, entry, device_id, device_name, user_name),
        ])

    # Add all sensors
    async_add_entities(server_sensors + device_sensors)


class EmbyDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Emby data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EmbyAPIClient,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Emby."""
        try:
            data = await self.client.get_dashboard_overview()
            _LOGGER.debug("Successfully updated Emby data")
            return data
        except EmbyAPIError as err:
            _LOGGER.error("Error fetching Emby data: %s", err)
            raise UpdateFailed(f"Error fetching Emby data: {err}") from err


class EmbySensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Emby sensors."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
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
        """Return device info - for server-level sensors."""
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


class EmbyDeviceSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Emby device-level sensors."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
        device_id: str,
        device_name: str,
        user_name: str = "",
    ) -> None:
        """Initialize the device sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.sensor_type = sensor_type
        self.device_id = device_id
        self.device_name = device_name
        self.user_name = user_name
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info - creates independent device entry."""
        system_info = {}
        if self.coordinator.data:
            system_info = self.coordinator.data.get("system_info", {})
        server_id = system_info.get("Id", self.entry.entry_id)

        # Create unique device identifier for this monitored device
        device_identifier = f"{server_id}_device_{self.device_id}"

        # Get app/client name from coordinator data if available
        app_name = "Emby Client"
        sessions = self.coordinator.data.get("sessions", []) if self.coordinator.data else []
        for session in sessions:
            session_device_id = session.get("DeviceId")
            session_internal_id = str(session.get("InternalDeviceId", ""))
            if session_device_id == self.device_id or session_internal_id == self.device_id:
                app_name = session.get("Client", app_name)
                break

        return {
            "identifiers": {(DOMAIN, device_identifier)},
            "name": f"Emby - {self.device_name}" + (f" ({self.user_name})" if self.user_name else ""),
            "manufacturer": "buynow",
            "model": app_name,
            "via_device": (DOMAIN, server_id),  # Link to server device
        }


class EmbyVersionSensor(EmbySensorBase):
    """Emby server version sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_VERSION)
        self._attr_name = "Emby 版本"
        self._attr_icon = ICON_VERSION

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        system_info = self.coordinator.data.get("system_info", {})
        return system_info.get("Version")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        system_info = self.coordinator.data.get("system_info", {})
        return {
            ATTR_SERVER_ID: system_info.get("Id"),
            ATTR_OPERATING_SYSTEM: system_info.get("OperatingSystem"),
        }


class EmbyServerNameSensor(EmbySensorBase):
    """Emby server name sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_SERVER_NAME)
        self._attr_name = "Emby 服务器名称"
        self._attr_icon = ICON_SERVER

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        system_info = self.coordinator.data.get("system_info", {})
        return system_info.get("ServerName")


class EmbyMovieCountSensor(EmbySensorBase):
    """Emby movie count sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_MOVIE_COUNT)
        self._attr_name = "Emby 电影数量"
        self._attr_icon = ICON_MOVIE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state."""
        items_counts = self.coordinator.data.get("items_counts", {})
        return items_counts.get("MovieCount", 0)


class EmbySeriesCountSensor(EmbySensorBase):
    """Emby series count sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_SERIES_COUNT)
        self._attr_name = "Emby 剧集数量"
        self._attr_icon = ICON_TV
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state."""
        items_counts = self.coordinator.data.get("items_counts", {})
        return items_counts.get("SeriesCount", 0)


class EmbyEpisodeCountSensor(EmbySensorBase):
    """Emby episode count sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_EPISODE_COUNT)
        self._attr_name = "Emby 集数"
        self._attr_icon = ICON_EPISODE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state."""
        items_counts = self.coordinator.data.get("items_counts", {})
        return items_counts.get("EpisodeCount", 0)


class EmbyTotalItemsSensor(EmbySensorBase):
    """Emby total items sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_TOTAL_ITEMS)
        self._attr_name = "Emby 总媒体数"
        self._attr_icon = ICON_TOTAL
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state."""
        items_counts = self.coordinator.data.get("items_counts", {})
        movie_count = items_counts.get("MovieCount", 0)
        series_count = items_counts.get("SeriesCount", 0)
        episode_count = items_counts.get("EpisodeCount", 0)
        return movie_count + series_count + episode_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        items_counts = self.coordinator.data.get("items_counts", {})
        return {
            ATTR_MOVIE_COUNT: items_counts.get("MovieCount", 0),
            ATTR_SERIES_COUNT: items_counts.get("SeriesCount", 0),
            ATTR_EPISODE_COUNT: items_counts.get("EpisodeCount", 0),
            ATTR_GAME_COUNT: items_counts.get("GameCount", 0),
            ATTR_ARTIST_COUNT: items_counts.get("ArtistCount", 0),
            ATTR_SONG_COUNT: items_counts.get("SongCount", 0),
            ATTR_ALBUM_COUNT: items_counts.get("AlbumCount", 0),
        }


class EmbyLibraryFoldersSensor(EmbySensorBase):
    """Emby library folders sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_LIBRARY_FOLDERS)
        self._attr_name = "Emby 媒体库数量"
        self._attr_icon = ICON_FOLDER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state."""
        library_folders = self.coordinator.data.get("library_folders", {})
        items = library_folders.get("Items", [])
        return len(items)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        library_folders = self.coordinator.data.get("library_folders", {})
        items = library_folders.get("Items", [])
        folders = [
            {
                "name": item.get("Name"),
                "id": item.get("Id"),
                "type": item.get("Type"),
            }
            for item in items
        ]
        return {ATTR_FOLDERS: folders}


class EmbyTotalUsersSensor(EmbySensorBase):
    """Emby total users sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_TOTAL_USERS)
        self._attr_name = "Emby 用户总数"
        self._attr_icon = ICON_USERS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state."""
        users = self.coordinator.data.get("users", [])
        return len(users)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        users = self.coordinator.data.get("users", [])
        user_list = [
            {
                "name": user.get("Name"),
                "id": user.get("Id"),
                "last_login": user.get("LastLoginDate"),
            }
            for user in users
        ]
        return {ATTR_USERS: user_list}


class EmbyActiveSessionsSensor(EmbySensorBase):
    """Emby active sessions sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_ACTIVE_SESSIONS)
        self._attr_name = "Emby 活动会话数"
        self._attr_icon = ICON_SESSION
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state."""
        sessions = self.coordinator.data.get("sessions", [])
        return len(sessions)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        sessions = self.coordinator.data.get("sessions", [])
        session_list = [
            {
                "client": session.get("Client"),
                "device": session.get("DeviceName"),
                "user": session.get("UserName"),
                "id": session.get("Id"),
            }
            for session in sessions
        ]
        return {ATTR_SESSIONS: session_list}


class EmbyDeviceCountSensor(EmbySensorBase):
    """Emby device count sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_DEVICE_COUNT)
        self._attr_name = "Emby 设备数量"
        self._attr_icon = ICON_DEVICE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state."""
        devices = self.coordinator.data.get("devices", {})
        items = devices.get("Items", [])
        return len(items)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        devices = self.coordinator.data.get("devices", {})
        items = devices.get("Items", [])
        device_list = [
            {
                "name": device.get("Name"),
                "app": device.get("AppName"),
                "last_activity": device.get("DateLastActivity"),
            }
            for device in items
        ]
        return {ATTR_DEVICES: device_list}


class EmbyRecentActivitiesSensor(EmbySensorBase):
    """Emby recent activities sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_RECENT_ACTIVITIES)
        self._attr_name = "Emby 最近活动"
        self._attr_icon = ICON_ACTIVITY
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state."""
        activity_log = self.coordinator.data.get("activity_log", {})
        items = activity_log.get("Items", [])
        return len(items)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        activity_log = self.coordinator.data.get("activity_log", {})
        items = activity_log.get("Items", [])
        activities = [
            {
                "name": item.get("Name"),
                "type": item.get("Type"),
                "date": item.get("Date"),
                "severity": item.get("Severity"),
            }
            for item in items
        ]
        return {ATTR_ACTIVITIES: activities}


class EmbyScheduledTasksSensor(EmbySensorBase):
    """Emby scheduled tasks sensor."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_SCHEDULED_TASKS)
        self._attr_name = "Emby 计划任务数"
        self._attr_icon = ICON_TASK
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state."""
        scheduled_tasks = self.coordinator.data.get("scheduled_tasks", [])
        return len(scheduled_tasks)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        scheduled_tasks = self.coordinator.data.get("scheduled_tasks", [])
        tasks = [
            {
                "name": task.get("Name"),
                "state": task.get("State"),
                "category": task.get("Category"),
            }
            for task in scheduled_tasks
        ]
        return {ATTR_TASKS: tasks}


class EmbyNowPlayingSensor(EmbyDeviceSensorBase):
    """Emby now playing sensor - shows current playback information."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
        device_id: str,
        device_name: str,
        user_name: str = "",
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            entry,
            f"{SENSOR_TYPE_NOW_PLAYING}_{device_id}",
            device_id,
            device_name,
            user_name,
        )
        self._attr_name = f"Emby {device_name} 当前播放"
        self._attr_icon = ICON_PLAY
        self._device_filter = device_id

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
    def native_value(self) -> str:
        """Return the state - currently playing content name."""
        sessions = self.coordinator.data.get("sessions", [])

        # Find first active playback session matching device filter
        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                media_name = now_playing.get("Name", "Unknown")
                media_type = now_playing.get("Type", "")

                # For episodes, include series name
                if media_type == "Episode":
                    series_name = now_playing.get("SeriesName", "")
                    season = now_playing.get("ParentIndexNumber")
                    episode = now_playing.get("IndexNumber")
                    if series_name and season and episode:
                        return f"{series_name} S{season:02d}E{episode:02d}"

                return media_name

        return "无播放"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes with detailed playback information."""
        sessions = self.coordinator.data.get("sessions", [])

        # Collect all active playback sessions matching device filter
        active_playbacks = []
        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if not now_playing:
                continue

            play_state = session.get("PlayState", {})
            media_type = now_playing.get("Type", "Unknown")

            # Determine media type in Chinese
            media_type_cn = {
                "Movie": "电影",
                "Episode": "剧集",
                "Video": "视频",
                "Audio": "音频",
                "Music": "音乐",
            }.get(media_type, media_type)

            # Calculate progress percentage
            position_ticks = play_state.get("PositionTicks", 0)
            runtime_ticks = now_playing.get("RunTimeTicks", 0)
            progress_percent = 0
            if runtime_ticks > 0:
                progress_percent = int((position_ticks / runtime_ticks) * 100)

            # Determine playback state
            is_paused = play_state.get("IsPaused", False)
            playback_state = "暂停" if is_paused else "播放中"

            playback_info = {
                "media_name": now_playing.get("Name"),
                "media_type": media_type_cn,
                "original_type": media_type,
                "playback_state": playback_state,
                "is_paused": is_paused,
                "progress_percent": progress_percent,
                "user": session.get("UserName", "Unknown"),
                "device": session.get("DeviceName", "Unknown"),
                "client": session.get("Client", "Unknown"),
            }

            # Add series-specific info
            if media_type == "Episode":
                playback_info.update({
                    "series_name": now_playing.get("SeriesName"),
                    "season": now_playing.get("ParentIndexNumber"),
                    "episode": now_playing.get("IndexNumber"),
                })

            # Add movie-specific info
            elif media_type == "Movie":
                playback_info.update({
                    "year": now_playing.get("ProductionYear"),
                })

            # Add position info
            if position_ticks and runtime_ticks:
                position_seconds = int(position_ticks / 10000000)
                runtime_seconds = int(runtime_ticks / 10000000)

                position_minutes = position_seconds // 60
                runtime_minutes = runtime_seconds // 60

                playback_info.update({
                    "position": f"{position_minutes}分钟",
                    "duration": f"{runtime_minutes}分钟",
                    "remaining": f"{runtime_minutes - position_minutes}分钟",
                })

            active_playbacks.append(playback_info)

        # Build base result
        result = {
            "active_count": len(active_playbacks),
        }

        # Add device filter info
        if self._device_filter and self._device_filter != "all":
            result["device_filter"] = self._device_filter
            result["device_filter_enabled"] = True
        else:
            result["device_filter"] = "所有设备"
            result["device_filter_enabled"] = False

        if not active_playbacks:
            result["status"] = "无活动播放"
            return result

        # Add first playback info to main attributes
        result.update(active_playbacks[0])

        # If multiple playbacks, add all to list
        if len(active_playbacks) > 1:
            result["all_playbacks"] = active_playbacks

        return result


class EmbyPlaybackStateSensor(EmbyDeviceSensorBase):
    """Emby playback state sensor - shows playing/paused/idle."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
        device_id: str,
        device_name: str,
        user_name: str = "",
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            entry,
            f"{SENSOR_TYPE_PLAYBACK_STATE}_{device_id}",
            device_id,
            device_name,
            user_name,
        )
        self._attr_name = f"Emby {device_name} 播放状态"
        self._attr_icon = ICON_PLAY
        self._device_filter = device_id

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
    def native_value(self) -> str:
        """Return the playback state."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                play_state = session.get("PlayState", {})
                is_paused = play_state.get("IsPaused", False)
                return "暂停" if is_paused else "播放中"

        return "空闲"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                play_state = session.get("PlayState", {})
                return {
                    "is_paused": play_state.get("IsPaused", False),
                    "is_muted": play_state.get("IsMuted", False),
                    "can_seek": play_state.get("CanSeek", False),
                    "device": session.get("DeviceName"),
                    "user": session.get("UserName"),
                }

        return {"status": "无活动播放"}


class EmbyMediaTypeSensor(EmbySensorBase):
    """Emby media type sensor - shows movie/episode/video."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_MEDIA_TYPE)
        self._attr_name = "Emby 媒体类型"
        self._attr_icon = ICON_MOVIE
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
    def native_value(self) -> str:
        """Return the media type."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                media_type = now_playing.get("Type", "Unknown")
                # Convert to Chinese
                type_map = {
                    "Movie": "电影",
                    "Episode": "电视剧",
                    "Video": "视频",
                    "Audio": "音频",
                    "Music": "音乐",
                }
                return type_map.get(media_type, media_type)

        return "无"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                attrs = {
                    "original_type": now_playing.get("Type"),
                }

                # Add series info if it's an episode
                if now_playing.get("Type") == "Episode":
                    attrs.update({
                        "series_name": now_playing.get("SeriesName"),
                        "season": now_playing.get("ParentIndexNumber"),
                        "episode": now_playing.get("IndexNumber"),
                    })

                # Add year if it's a movie
                elif now_playing.get("Type") == "Movie":
                    attrs["year"] = now_playing.get("ProductionYear")

                return attrs

        return {"status": "无活动播放"}


class EmbyMediaTitleSensor(EmbySensorBase):
    """Emby media title sensor - shows current playing media name."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_MEDIA_TITLE)
        self._attr_name = "Emby 媒体名称"
        self._attr_icon = ICON_PLAY
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
    def native_value(self) -> str:
        """Return the media title."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                media_name = now_playing.get("Name", "Unknown")
                media_type = now_playing.get("Type", "")

                # For episodes, show series S01E01 format
                if media_type == "Episode":
                    series_name = now_playing.get("SeriesName", "")
                    season = now_playing.get("ParentIndexNumber")
                    episode = now_playing.get("IndexNumber")
                    if series_name and season and episode:
                        return f"{series_name} S{season:02d}E{episode:02d} - {media_name}"

                return media_name

        return "无"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                play_state = session.get("PlayState", {})
                position_ticks = play_state.get("PositionTicks", 0)
                runtime_ticks = now_playing.get("RunTimeTicks", 0)

                # Calculate progress
                progress_percent = 0
                if runtime_ticks > 0:
                    progress_percent = int((position_ticks / runtime_ticks) * 100)

                attrs = {
                    "media_id": now_playing.get("Id"),
                    "progress_percent": progress_percent,
                    "device": session.get("DeviceName"),
                    "user": session.get("UserName"),
                }

                # Add time info
                if position_ticks and runtime_ticks:
                    position_minutes = int(position_ticks / 10000000 / 60)
                    runtime_minutes = int(runtime_ticks / 10000000 / 60)
                    attrs.update({
                        "position": f"{position_minutes}分钟",
                        "duration": f"{runtime_minutes}分钟",
                        "remaining": f"{runtime_minutes - position_minutes}分钟",
                    })

                return attrs

        return {"status": "无活动播放"}


class EmbyProgressPercentSensor(EmbyDeviceSensorBase):
    """Emby progress percent sensor - shows playback progress percentage."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
        device_id: str,
        device_name: str,
        user_name: str = "",
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            entry,
            f"{SENSOR_TYPE_PROGRESS_PERCENT}_{device_id}",
            device_id,
            device_name,
            user_name,
        )
        self._attr_name = f"Emby {device_name} 播放进度"
        self._attr_icon = ICON_PLAY
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._device_filter = device_id

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
    def native_value(self) -> int:
        """Return the progress percentage."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                play_state = session.get("PlayState", {})
                position_ticks = play_state.get("PositionTicks", 0)
                runtime_ticks = now_playing.get("RunTimeTicks", 0)

                if runtime_ticks > 0:
                    return int((position_ticks / runtime_ticks) * 100)

        return 0


class EmbyPlaybackPositionSensor(EmbySensorBase):
    """Emby playback position sensor - shows current playback position."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_PLAYBACK_POSITION)
        self._attr_name = "Emby 播放位置"
        self._attr_icon = ICON_PLAY
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
    def native_value(self) -> str:
        """Return the playback position."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                play_state = session.get("PlayState", {})
                position_ticks = play_state.get("PositionTicks", 0)

                if position_ticks > 0:
                    position_seconds = int(position_ticks / 10000000)
                    hours = position_seconds // 3600
                    minutes = (position_seconds % 3600) // 60
                    seconds = position_seconds % 60

                    if hours > 0:
                        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        return f"{minutes:02d}:{seconds:02d}"

        return "00:00"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                play_state = session.get("PlayState", {})
                position_ticks = play_state.get("PositionTicks", 0)
                position_seconds = int(position_ticks / 10000000)

                return {
                    "position_seconds": position_seconds,
                    "position_minutes": position_seconds // 60,
                }

        return {}


class EmbyPlaybackRemainingSensor(EmbyDeviceSensorBase):
    """Emby playback remaining sensor - shows remaining playback time."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
        device_id: str,
        device_name: str,
        user_name: str = "",
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            entry,
            f"{SENSOR_TYPE_PLAYBACK_REMAINING}_{device_id}",
            device_id,
            device_name,
            user_name,
        )
        self._attr_name = f"Emby {device_name} 剩余时间"
        self._attr_icon = ICON_PLAY
        self._device_filter = device_id

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
    def native_value(self) -> str:
        """Return the remaining time."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                play_state = session.get("PlayState", {})
                position_ticks = play_state.get("PositionTicks", 0)
                runtime_ticks = now_playing.get("RunTimeTicks", 0)

                if runtime_ticks > 0 and position_ticks > 0:
                    remaining_ticks = runtime_ticks - position_ticks
                    remaining_seconds = int(remaining_ticks / 10000000)
                    hours = remaining_seconds // 3600
                    minutes = (remaining_seconds % 3600) // 60
                    seconds = remaining_seconds % 60

                    if hours > 0:
                        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        return f"{minutes:02d}:{seconds:02d}"

        return "00:00"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                play_state = session.get("PlayState", {})
                position_ticks = play_state.get("PositionTicks", 0)
                runtime_ticks = now_playing.get("RunTimeTicks", 0)

                if runtime_ticks > 0 and position_ticks > 0:
                    remaining_ticks = runtime_ticks - position_ticks
                    remaining_seconds = int(remaining_ticks / 10000000)

                    return {
                        "remaining_seconds": remaining_seconds,
                        "remaining_minutes": remaining_seconds // 60,
                    }

        return {}


class EmbySubtitleTrackSensor(EmbySensorBase):
    """Emby subtitle track sensor - shows current subtitle track."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_SUBTITLE_TRACK)
        self._attr_name = "Emby 字幕轨道"
        self._attr_icon = "mdi:subtitles"
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
    def native_value(self) -> str:
        """Return the current subtitle track."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                # Get media streams
                media_streams = now_playing.get("MediaStreams", [])
                play_state = session.get("PlayState", {})
                
                # Get current subtitle index
                subtitle_stream_index = play_state.get("SubtitleStreamIndex")
                
                # Find subtitle tracks
                subtitle_tracks = [
                    stream for stream in media_streams
                    if stream.get("Type") == "Subtitle"
                ]
                
                if not subtitle_tracks:
                    return "无字幕"
                
                # Find current subtitle
                if subtitle_stream_index is not None:
                    for track in subtitle_tracks:
                        if track.get("Index") == subtitle_stream_index:
                            language = track.get("DisplayLanguage", track.get("Language", "未知"))
                            title = track.get("DisplayTitle", "")
                            codec = track.get("Codec", "")
                            is_default = track.get("IsDefault", False)
                            is_forced = track.get("IsForced", False)
                            
                            name = language
                            if title and title != language:
                                name = f"{language} - {title}"
                            if is_forced:
                                name += " (强制)"
                            if is_default:
                                name += " (默认)"
                                
                            return name
                
                return "关闭"

        return "无播放"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                media_streams = now_playing.get("MediaStreams", [])
                play_state = session.get("PlayState", {})
                subtitle_stream_index = play_state.get("SubtitleStreamIndex")
                
                # Get all subtitle tracks
                subtitle_tracks = []
                current_subtitle = None
                
                for stream in media_streams:
                    if stream.get("Type") == "Subtitle":
                        track_info = {
                            "index": stream.get("Index"),
                            "language": stream.get("DisplayLanguage", stream.get("Language", "未知")),
                            "codec": stream.get("Codec"),
                            "is_default": stream.get("IsDefault", False),
                            "is_forced": stream.get("IsForced", False),
                            "is_external": stream.get("IsExternal", False),
                            "title": stream.get("DisplayTitle", ""),
                        }
                        subtitle_tracks.append(track_info)
                        
                        if subtitle_stream_index == stream.get("Index"):
                            current_subtitle = track_info
                
                return {
                    "available_tracks": subtitle_tracks,
                    "track_count": len(subtitle_tracks),
                    "current_index": subtitle_stream_index,
                    "current_track": current_subtitle,
                    "has_subtitles": len(subtitle_tracks) > 0,
                    "subtitles_enabled": subtitle_stream_index is not None,
                }

        return {"status": "无活动播放"}


class EmbyAudioTrackSensor(EmbySensorBase):
    """Emby audio track sensor - shows current audio track."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_AUDIO_TRACK)
        self._attr_name = "Emby 音频轨道"
        self._attr_icon = "mdi:volume-high"
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
    def native_value(self) -> str:
        """Return the current audio track."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                # Get media streams
                media_streams = now_playing.get("MediaStreams", [])
                play_state = session.get("PlayState", {})
                
                # Get current audio index
                audio_stream_index = play_state.get("AudioStreamIndex")
                
                # Find audio tracks
                audio_tracks = [
                    stream for stream in media_streams
                    if stream.get("Type") == "Audio"
                ]
                
                if not audio_tracks:
                    return "无音频"
                
                # Find current audio track
                if audio_stream_index is not None:
                    for track in audio_tracks:
                        if track.get("Index") == audio_stream_index:
                            language = track.get("DisplayLanguage", track.get("Language", "未知"))
                            codec = track.get("Codec", "")
                            channels = track.get("Channels")
                            channel_layout = track.get("ChannelLayout", "")
                            is_default = track.get("IsDefault", False)
                            
                            name = language
                            if codec:
                                name += f" ({codec.upper()})"
                            if channels:
                                if channel_layout:
                                    name += f" {channel_layout}"
                                else:
                                    name += f" {channels}ch"
                            if is_default:
                                name += " (默认)"
                                
                            return name
                
                # If no specific track selected, use first one
                if audio_tracks:
                    track = audio_tracks[0]
                    language = track.get("DisplayLanguage", track.get("Language", "未知"))
                    codec = track.get("Codec", "")
                    return f"{language} ({codec.upper()})" if codec else language
                
                return "未知"

        return "无播放"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        sessions = self.coordinator.data.get("sessions", [])

        for session in sessions:
            if not self._should_include_session(session):
                continue

            now_playing = session.get("NowPlayingItem")
            if now_playing:
                media_streams = now_playing.get("MediaStreams", [])
                play_state = session.get("PlayState", {})
                audio_stream_index = play_state.get("AudioStreamIndex")
                
                # Get all audio tracks
                audio_tracks = []
                current_audio = None
                
                for stream in media_streams:
                    if stream.get("Type") == "Audio":
                        track_info = {
                            "index": stream.get("Index"),
                            "language": stream.get("DisplayLanguage", stream.get("Language", "未知")),
                            "codec": stream.get("Codec"),
                            "channels": stream.get("Channels"),
                            "channel_layout": stream.get("ChannelLayout"),
                            "bitrate": stream.get("BitRate"),
                            "sample_rate": stream.get("SampleRate"),
                            "is_default": stream.get("IsDefault", False),
                            "title": stream.get("DisplayTitle", ""),
                        }
                        audio_tracks.append(track_info)
                        
                        if audio_stream_index == stream.get("Index"):
                            current_audio = track_info
                
                return {
                    "available_tracks": audio_tracks,
                    "track_count": len(audio_tracks),
                    "current_index": audio_stream_index,
                    "current_track": current_audio,
                    "has_audio": len(audio_tracks) > 0,
                }

        return {"status": "无活动播放"}


class EmbyTodayPlayCountSensor(EmbySensorBase):
    """Emby today play count sensor - shows playback count from activity log."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_TODAY_PLAY_COUNT)
        self._attr_name = "Emby 今日播放次数"
        self._attr_icon = "mdi:play-circle-outline"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return today's play count from activity log."""
        from datetime import datetime, timedelta
        
        activity_log = self.coordinator.data.get("activity_log", {})
        items = activity_log.get("Items", [])
        
        # Get today's date
        today = datetime.now().date()
        play_count = 0
        
        # Count playback activities from today
        for item in items:
            # Check if it's a playback activity
            item_type = item.get("Type", "")
            if "Playback" in item_type or item_type == "PlaybackStart":
                # Parse date
                date_str = item.get("Date", "")
                if date_str:
                    try:
                        item_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                        if item_date == today:
                            play_count += 1
                    except (ValueError, AttributeError):
                        pass
        
        return play_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        from datetime import datetime
        
        activity_log = self.coordinator.data.get("activity_log", {})
        items = activity_log.get("Items", [])
        today = datetime.now().date()
        
        today_playbacks = []
        for item in items:
            item_type = item.get("Type", "")
            if "Playback" in item_type or item_type == "PlaybackStart":
                date_str = item.get("Date", "")
                if date_str:
                    try:
                        item_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                        if item_date == today:
                            today_playbacks.append({
                                "name": item.get("Name", "Unknown"),
                                "type": item.get("Type"),
                                "user": item.get("UserName"),
                                "date": date_str,
                            })
                    except (ValueError, AttributeError):
                        pass
        
        return {
            "playbacks": today_playbacks[:10],  # Limit to 10 most recent
            "note": "基于活动日志统计，可能不完全准确",
        }


class EmbyTodayWatchTimeSensor(EmbySensorBase):
    """Emby today watch time sensor - shows total watch time today."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_TODAY_WATCH_TIME)
        self._attr_name = "Emby 今日观看时长"
        self._attr_icon = "mdi:clock-outline"
        self._attr_native_unit_of_measurement = "分钟"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self) -> int:
        """Return today's watch time in minutes."""
        # Note: This is a simplified implementation
        # True watch time tracking would require storing session data
        # Currently showing estimated time based on activity log
        
        from datetime import datetime
        
        activity_log = self.coordinator.data.get("activity_log", {})
        items = activity_log.get("Items", [])
        today = datetime.now().date()
        
        # Count playback activities and estimate watch time
        playback_count = 0
        for item in items:
            item_type = item.get("Type", "")
            if "Playback" in item_type or item_type == "PlaybackStart":
                date_str = item.get("Date", "")
                if date_str:
                    try:
                        item_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                        if item_date == today:
                            playback_count += 1
                    except (ValueError, AttributeError):
                        pass
        
        # Rough estimate: assume average 30 minutes per playback
        # This is not accurate - real implementation would need session tracking
        estimated_minutes = playback_count * 30
        
        return estimated_minutes

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        from datetime import datetime
        
        activity_log = self.coordinator.data.get("activity_log", {})
        items = activity_log.get("Items", [])
        today = datetime.now().date()
        
        playback_count = 0
        for item in items:
            item_type = item.get("Type", "")
            if "Playback" in item_type or item_type == "PlaybackStart":
                date_str = item.get("Date", "")
                if date_str:
                    try:
                        item_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                        if item_date == today:
                            playback_count += 1
                    except (ValueError, AttributeError):
                        pass
        
        estimated_minutes = playback_count * 30
        hours = estimated_minutes // 60
        minutes = estimated_minutes % 60
        
        return {
            "playback_count": playback_count,
            "estimated_hours": hours,
            "estimated_minutes": minutes,
            "formatted_time": f"{hours}小时{minutes}分钟",
            "note": "基于播放次数估算（平均30分钟/次），非实际观看时长",
            "warning": "需要实现会话跟踪才能获得准确的观看时长",
        }


class EmbyRecentlyAddedSensor(EmbySensorBase):
    """Emby recently added sensor - shows recently added media name."""

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TYPE_RECENTLY_ADDED)
        self._attr_name = "Emby 最近添加"
        self._attr_icon = "mdi:new-box"

    @property
    def native_value(self) -> str:
        """Return the most recently added media name."""
        activity_log = self.coordinator.data.get("activity_log", {})
        items = activity_log.get("Items", [])

        # Find most recent added item from last 7 days
        from datetime import datetime, timedelta

        week_ago = datetime.now() - timedelta(days=7)
        recently_added = []

        for item in items:
            item_type = item.get("Type", "")
            # Look for item creation/addition activities
            if any(keyword in item_type for keyword in ["Added", "Create", "New"]):
                date_str = item.get("Date", "")
                if date_str:
                    try:
                        item_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        if item_date >= week_ago:
                            recently_added.append({
                                "name": item.get("Name", "Unknown"),
                                "date": item_date,
                            })
                    except (ValueError, AttributeError):
                        pass

        # Sort by date, newest first
        if recently_added:
            recently_added.sort(key=lambda x: x.get("date"), reverse=True)
            return recently_added[0]["name"]

        return "无新增"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        from datetime import datetime, timedelta

        activity_log = self.coordinator.data.get("activity_log", {})
        items = activity_log.get("Items", [])
        week_ago = datetime.now() - timedelta(days=7)

        recently_added = []
        for item in items:
            item_type = item.get("Type", "")
            if any(keyword in item_type for keyword in ["Added", "Create", "New"]):
                date_str = item.get("Date", "")
                if date_str:
                    try:
                        item_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        if item_date >= week_ago:
                            recently_added.append({
                                "name": item.get("Name", "Unknown"),
                                "type": item.get("Type"),
                                "date": date_str,
                                "severity": item.get("Severity"),
                            })
                    except (ValueError, AttributeError):
                        pass

        # Sort by date, newest first
        recently_added.sort(key=lambda x: x.get("date", ""), reverse=True)

        return {
            "total_count": len(recently_added),  # 总数量
            "latest_item": recently_added[0]["name"] if recently_added else "无",  # 最新项
            "latest_date": recently_added[0]["date"] if recently_added else None,  # 最新日期
            "all_items": recently_added[:20],  # 所有项（最多20个）
            "time_range": "最近7天",
            "note": "基于活动日志统计，显示最近7天添加的媒体",
        }
