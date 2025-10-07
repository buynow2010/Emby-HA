"""Media player platform for Emby integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ICON_PLAY,
    INTEGRATION_VERSION,
    MEDIA_TYPE_AUDIO,
    MEDIA_TYPE_VIDEO,
    SESSION_STATE_IDLE,
    SESSION_STATE_PAUSED,
    SESSION_STATE_PLAYING,
)
from .sensor import EmbyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby media player entries."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Get monitored devices from options
    monitored_devices = entry.options.get("monitored_devices", [])

    # Create media player entities for each monitored device
    media_players = []
    for device in monitored_devices:
        device_id = device["device_id"]
        device_name = device["device_name"]
        user_name = device.get("user_name", "")

        _LOGGER.info(
            "Creating media player for device: %s (ID: %s, User: %s)",
            device_name,
            device_id,
            user_name
        )

        media_players.append(
            EmbyMediaPlayer(coordinator, entry, device_id, device_name, user_name)
        )

    if media_players:
        async_add_entities(media_players)
        _LOGGER.info("Created %d media player entities", len(media_players))
    else:
        _LOGGER.info("No monitored devices configured, no media players created")


class EmbyMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    """Emby media player entity for a session."""

    _attr_device_class = MediaPlayerDeviceClass.TV
    # Only enable informational features, no control features
    # MediaPlayerEntityFeature(0) with manual state reporting
    # We don't use PAUSE/PLAY/STOP as Infuse doesn't support remote control
    _attr_supported_features = MediaPlayerEntityFeature(0)

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        entry: ConfigEntry,
        device_id: str,
        device_name: str,
        user_name: str,
    ) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self.entry = entry
        self.device_id = device_id
        self.device_name = device_name
        self.user_name = user_name
        self._attr_unique_id = f"{entry.entry_id}_media_player_{device_id}"
        self._session_data = None
        # Cache device info to keep entity available when session ends
        self._cached_user = user_name
        self._cached_device = device_name
        self._cached_client = "Unknown"
        self._update_session_data()

        _LOGGER.info(
            "Initialized media player for device %s: unique_id=%s, has_session_data=%s",
            device_id,
            self._attr_unique_id,
            self._session_data is not None
        )

    def _update_session_data(self) -> None:
        """Update session data from coordinator."""
        # Safely handle case where coordinator data might be None
        if not self.coordinator.data:
            self._session_data = None
            _LOGGER.debug("Device %s: coordinator.data is None", self.device_id)
            return

        sessions = self.coordinator.data.get("sessions", [])
        _LOGGER.debug(
            "Device %s: checking %d sessions for match",
            self.device_id,
            len(sessions)
        )

        # Find session matching this device
        for session in sessions:
            session_device_id = session.get("DeviceId")
            session_internal_id = str(session.get("InternalDeviceId", ""))

            if session_device_id == self.device_id or session_internal_id == self.device_id:
                self._session_data = session
                # Update cached info from live session
                self._cached_user = session.get("UserName", self._cached_user)
                self._cached_device = session.get("DeviceName", self._cached_device)
                self._cached_client = session.get("Client", self._cached_client)
                _LOGGER.debug(
                    "Device %s: found matching session, user=%s, device=%s",
                    self.device_id,
                    self._cached_user,
                    self._cached_device
                )
                return

        self._session_data = None
        _LOGGER.debug("Device %s: no matching session found", self.device_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_session_data()
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Check coordinator is available and has data
        is_available = self.coordinator.last_update_success

        # Log availability status for debugging
        if not is_available:
            _LOGGER.warning(
                "Media player %s unavailable: coordinator.last_update_success=%s, coordinator.data=%s",
                self.unique_id,
                self.coordinator.last_update_success,
                self.coordinator.data is not None
            )

        return is_available

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        # Use cached info if session data is not available
        user = self._cached_user or self.user_name
        device = self._cached_device or self.device_name

        if self._session_data:
            user = self._session_data.get("UserName", user)
            device = self._session_data.get("DeviceName", device)

        return f"Emby {user} - {device}"

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the entity."""
        if not self._session_data:
            # Show as idle when session ends, not off
            return MediaPlayerState.IDLE

        now_playing = self._session_data.get("NowPlayingItem")
        if not now_playing:
            return MediaPlayerState.IDLE

        play_state = self._session_data.get("PlayState", {})
        is_paused = play_state.get("IsPaused", False)

        if is_paused:
            return MediaPlayerState.PAUSED
        else:
            return MediaPlayerState.PLAYING

    @property
    def media_content_type(self) -> str:
        """Return the content type of current playing media."""
        if not self._session_data:
            return None

        now_playing = self._session_data.get("NowPlayingItem", {})
        item_type = now_playing.get("Type", "").lower()

        if item_type in ["movie", "episode", "video"]:
            return MediaType.VIDEO
        elif item_type in ["audio", "music", "song"]:
            return MediaType.MUSIC
        else:
            return None

    @property
    def media_title(self) -> str | None:
        """Return the title of current playing media."""
        if not self._session_data:
            return None

        now_playing = self._session_data.get("NowPlayingItem", {})
        return now_playing.get("Name")

    @property
    def media_series_title(self) -> str | None:
        """Return the series title if playing an episode."""
        if not self._session_data:
            return None

        now_playing = self._session_data.get("NowPlayingItem", {})
        if now_playing.get("Type") == "Episode":
            return now_playing.get("SeriesName")
        return None

    @property
    def media_season(self) -> str | None:
        """Return the season number if playing an episode."""
        if not self._session_data:
            return None

        now_playing = self._session_data.get("NowPlayingItem", {})
        if now_playing.get("Type") == "Episode":
            season = now_playing.get("ParentIndexNumber")
            return f"S{season}" if season else None
        return None

    @property
    def media_episode(self) -> str | None:
        """Return the episode number if playing an episode."""
        if not self._session_data:
            return None

        now_playing = self._session_data.get("NowPlayingItem", {})
        if now_playing.get("Type") == "Episode":
            episode = now_playing.get("IndexNumber")
            return f"E{episode}" if episode else None
        return None

    @property
    def media_duration(self) -> int | None:
        """Return the duration of current playing media in seconds."""
        if not self._session_data:
            return None

        now_playing = self._session_data.get("NowPlayingItem", {})
        run_time_ticks = now_playing.get("RunTimeTicks")
        if run_time_ticks:
            # Convert from ticks (100-nanosecond intervals) to seconds
            return int(run_time_ticks / 10000000)
        return None

    @property
    def media_position(self) -> int | None:
        """Return the position of current playing media in seconds."""
        if not self._session_data:
            return None

        play_state = self._session_data.get("PlayState", {})
        position_ticks = play_state.get("PositionTicks")
        if position_ticks:
            # Convert from ticks to seconds
            return int(position_ticks / 10000000)
        return None

    @property
    def media_image_url(self) -> str | None:
        """Return the image URL of current playing media."""
        if not self._session_data:
            return None

        now_playing = self._session_data.get("NowPlayingItem", {})
        item_id = now_playing.get("Id")
        if item_id:
            # Construct image URL
            base_url = self.coordinator.client.base_url
            api_key = self.coordinator.client.api_key
            return f"{base_url}/Items/{item_id}/Images/Primary?api_key={api_key}"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        # Always show cached device info even when not playing
        attrs = {
            "device_id": self.device_id,
            "client": self._cached_client,
            "device_name": self._cached_device,
            "user_name": self._cached_user,
        }

        if not self._session_data:
            attrs["status"] = "空闲"
            return attrs

        play_state = self._session_data.get("PlayState", {})
        now_playing = self._session_data.get("NowPlayingItem", {})

        # Update with live session data
        attrs.update({
            "session_id": self._session_data.get("Id"),
            "client": self._session_data.get("Client"),
            "device_name": self._session_data.get("DeviceName"),
            "user_name": self._session_data.get("UserName"),
            "remote_endpoint": self._session_data.get("RemoteEndPoint"),
            "is_muted": play_state.get("IsMuted", False),
            "can_seek": play_state.get("CanSeek", False),
            "repeat_mode": play_state.get("RepeatMode"),
        })

        if now_playing:
            attrs.update({
                "media_type": now_playing.get("Type"),
                "media_id": now_playing.get("Id"),
                "production_year": now_playing.get("ProductionYear"),
            })

        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info - creates independent device entry."""
        system_info = {}
        if self.coordinator.data:
            system_info = self.coordinator.data.get("system_info", {})
        server_id = system_info.get("Id", self.entry.entry_id)

        # Create unique device identifier for this monitored device
        device_identifier = f"{server_id}_device_{self.device_id}"

        # Get current client/app name from session if available
        app_name = "Emby Client"
        if self._session_data:
            app_name = self._session_data.get("Client", app_name)

        return {
            "identifiers": {(DOMAIN, device_identifier)},
            "name": f"Emby - {self.device_name}" + (f" ({self.user_name})" if self.user_name else ""),
            "manufacturer": "buynow",
            "model": app_name,
            "via_device": (DOMAIN, server_id),  # Link to server device
        }

    async def async_media_play(self) -> None:
        """Send play command."""
        _LOGGER.info("Play command for device %s", self.device_id)
        # TODO: Implement via /Sessions/{id}/Playing/Unpause

    async def async_media_pause(self) -> None:
        """Send pause command."""
        _LOGGER.info("Pause command for device %s", self.device_id)
        # TODO: Implement via /Sessions/{id}/Playing/Pause

    async def async_media_stop(self) -> None:
        """Send stop command."""
        _LOGGER.info("Stop command for device %s", self.device_id)
        # TODO: Implement via /Sessions/{id}/Playing/Stop

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        _LOGGER.info("Next track command for device %s", self.device_id)
        # TODO: Implement via /Sessions/{id}/Playing/NextTrack

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        _LOGGER.info("Previous track command for device %s", self.device_id)
        # TODO: Implement via /Sessions/{id}/Playing/PreviousTrack

    async def async_media_seek(self, position: float) -> None:
        """Send seek command."""
        _LOGGER.info("Seek command for device %s to position %s", self.device_id, position)
        # TODO: Implement via /Sessions/{id}/Playing/Seek
