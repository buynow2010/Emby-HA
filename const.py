"""Constants for the Emby integration."""
from datetime import timedelta
from typing import Final

# Integration info
DOMAIN: Final = "emby"
DEFAULT_NAME: Final = "Emby"
DEFAULT_PORT: Final = 8096
DEFAULT_SCAN_INTERVAL: Final = 30
INTEGRATION_VERSION: Final = "1.0.0"  # Integration version

# Configuration
CONF_API_KEY: Final = "api_key"
CONF_DEVICE_ID: Final = "device_id"

# API endpoints (all tested and verified - 11 working endpoints)
API_ENDPOINT_SYSTEM_INFO: Final = "/System/Info"
API_ENDPOINT_SYSTEM_INFO_PUBLIC: Final = "/System/Info/Public"
API_ENDPOINT_SYSTEM_ENDPOINT: Final = "/System/Endpoint"
API_ENDPOINT_ITEMS_COUNTS: Final = "/Items/Counts"
API_ENDPOINT_LIBRARY_FOLDERS: Final = "/Library/MediaFolders"
API_ENDPOINT_SESSIONS: Final = "/Sessions"
API_ENDPOINT_USERS: Final = "/Users"
API_ENDPOINT_USERS_PUBLIC: Final = "/Users/Public"
API_ENDPOINT_ACTIVITY_LOG: Final = "/System/ActivityLog/Entries"
API_ENDPOINT_SCHEDULED_TASKS: Final = "/ScheduledTasks"
API_ENDPOINT_DEVICES: Final = "/Devices"

# Update interval
UPDATE_INTERVAL: Final = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

# Sensor types
SENSOR_TYPE_VERSION: Final = "version"
SENSOR_TYPE_SERVER_NAME: Final = "server_name"
SENSOR_TYPE_MOVIE_COUNT: Final = "movie_count"
SENSOR_TYPE_SERIES_COUNT: Final = "series_count"
SENSOR_TYPE_EPISODE_COUNT: Final = "episode_count"
SENSOR_TYPE_TOTAL_ITEMS: Final = "total_items"
SENSOR_TYPE_LIBRARY_FOLDERS: Final = "library_folders"
SENSOR_TYPE_TOTAL_USERS: Final = "total_users"
SENSOR_TYPE_ACTIVE_SESSIONS: Final = "active_sessions"
SENSOR_TYPE_DEVICE_COUNT: Final = "device_count"
SENSOR_TYPE_RECENT_ACTIVITIES: Final = "recent_activities"
SENSOR_TYPE_SCHEDULED_TASKS: Final = "scheduled_tasks"
SENSOR_TYPE_NOW_PLAYING: Final = "now_playing"
SENSOR_TYPE_PLAYBACK_STATE: Final = "playback_state"
SENSOR_TYPE_MEDIA_TYPE: Final = "media_type_current"
SENSOR_TYPE_MEDIA_TITLE: Final = "media_title"
SENSOR_TYPE_PROGRESS_PERCENT: Final = "progress_percent"
SENSOR_TYPE_PLAYBACK_POSITION: Final = "playback_position"
SENSOR_TYPE_PLAYBACK_REMAINING: Final = "playback_remaining"
SENSOR_TYPE_SUBTITLE_TRACK: Final = "subtitle_track"
SENSOR_TYPE_AUDIO_TRACK: Final = "audio_track"
SENSOR_TYPE_TODAY_PLAY_COUNT: Final = "today_play_count"
SENSOR_TYPE_TODAY_WATCH_TIME: Final = "today_watch_time"
SENSOR_TYPE_RECENTLY_ADDED: Final = "recently_added"

# Binary sensor types
BINARY_SENSOR_TYPE_LIBRARY_SCANNING: Final = "library_scanning"
BINARY_SENSOR_TYPE_ONLINE: Final = "online"
BINARY_SENSOR_TYPE_ACTIVE_STREAMS: Final = "has_active_streams"
BINARY_SENSOR_TYPE_TASKS_RUNNING: Final = "tasks_running"
BINARY_SENSOR_TYPE_PENDING_RESTART: Final = "pending_restart"
BINARY_SENSOR_TYPE_IN_NETWORK: Final = "is_in_network"

# Button types
BUTTON_TYPE_REFRESH: Final = "refresh"
BUTTON_TYPE_TEST_CONNECTION: Final = "test_connection"

# Icons
ICON_SERVER: Final = "mdi:server"
ICON_VERSION: Final = "mdi:tag"
ICON_MOVIE: Final = "mdi:movie"
ICON_TV: Final = "mdi:television"
ICON_EPISODE: Final = "mdi:play-box-multiple"
ICON_FOLDER: Final = "mdi:folder-multiple"
ICON_USERS: Final = "mdi:account-multiple"
ICON_SESSION: Final = "mdi:monitor-multiple"
ICON_DEVICE: Final = "mdi:devices"
ICON_ACTIVITY: Final = "mdi:history"
ICON_TASK: Final = "mdi:calendar-clock"
ICON_REFRESH: Final = "mdi:refresh"
ICON_CONNECTION: Final = "mdi:connection"
ICON_ONLINE: Final = "mdi:check-network"
ICON_PLAY: Final = "mdi:play-circle"
ICON_RESTART: Final = "mdi:restart"
ICON_NETWORK: Final = "mdi:lan"
ICON_TOTAL: Final = "mdi:sigma"

# Device info
MANUFACTURER: Final = "Emby"
MODEL: Final = "Emby Server"

# Platforms
PLATFORMS: Final = ["sensor", "binary_sensor", "button", "media_player"]

# Error messages
ERROR_AUTH: Final = "Authentication failed"
ERROR_CONNECT: Final = "Connection failed"
ERROR_TIMEOUT: Final = "Request timeout"
ERROR_UNKNOWN: Final = "Unknown error"

# Media player constants
MEDIA_TYPE_VIDEO: Final = "video"
MEDIA_TYPE_AUDIO: Final = "audio"
MEDIA_TYPE_UNKNOWN: Final = "unknown"

# Session states
SESSION_STATE_PLAYING: Final = "playing"
SESSION_STATE_PAUSED: Final = "paused"
SESSION_STATE_IDLE: Final = "idle"

# Task states
TASK_STATE_IDLE: Final = "Idle"
TASK_STATE_RUNNING: Final = "Running"
TASK_STATE_CANCELLING: Final = "Cancelling"

# Sensor attributes
ATTR_SERVER_ID: Final = "server_id"
ATTR_OPERATING_SYSTEM: Final = "operating_system"
ATTR_VERSION: Final = "version"
ATTR_FOLDERS: Final = "folders"
ATTR_USERS: Final = "users"
ATTR_DEVICES: Final = "devices"
ATTR_ACTIVITIES: Final = "activities"
ATTR_TASKS: Final = "tasks"
ATTR_SESSIONS: Final = "sessions"
ATTR_MOVIE_COUNT: Final = "movie_count"
ATTR_SERIES_COUNT: Final = "series_count"
ATTR_EPISODE_COUNT: Final = "episode_count"
ATTR_GAME_COUNT: Final = "game_count"
ATTR_ARTIST_COUNT: Final = "artist_count"
ATTR_SONG_COUNT: Final = "song_count"
ATTR_ALBUM_COUNT: Final = "album_count"

# Default values
DEFAULT_TIMEOUT: Final = 10
