"""Emby API Client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import async_timeout

from .const import (
    API_ENDPOINT_ACTIVITY_LOG,
    API_ENDPOINT_DEVICES,
    API_ENDPOINT_ITEMS_COUNTS,
    API_ENDPOINT_LIBRARY_FOLDERS,
    API_ENDPOINT_SCHEDULED_TASKS,
    API_ENDPOINT_SESSIONS,
    API_ENDPOINT_SYSTEM_ENDPOINT,
    API_ENDPOINT_SYSTEM_INFO,
    API_ENDPOINT_SYSTEM_INFO_PUBLIC,
    API_ENDPOINT_USERS,
    DEFAULT_TIMEOUT,
    ERROR_AUTH,
    ERROR_CONNECT,
    ERROR_TIMEOUT,
    ERROR_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)


class EmbyAPIError(Exception):
    """Base exception for Emby API errors."""


class EmbyAuthError(EmbyAPIError):
    """Authentication error."""


class EmbyConnectionError(EmbyAPIError):
    """Connection error."""


class EmbyTimeoutError(EmbyAPIError):
    """Timeout error."""


class EmbyAPIClient:
    """Emby API Client."""

    def __init__(
        self,
        host: str,
        port: int,
        api_key: str,
        session: aiohttp.ClientSession,
        use_ssl: bool = False,
    ) -> None:
        """Initialize the API client.

        Args:
            host: Emby server hostname or IP
            port: Emby server port
            api_key: Emby API key
            session: aiohttp ClientSession
            use_ssl: Whether to use HTTPS
        """
        self.host = host
        self.port = port
        self.api_key = api_key
        self.session = session
        self.use_ssl = use_ssl
        self.base_url = f"{'https' if use_ssl else 'http'}://{host}:{port}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Any:
        """Make a request to the Emby API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: URL parameters
            timeout: Request timeout in seconds

        Returns:
            Response data (dict or list)

        Raises:
            EmbyAuthError: Authentication failed
            EmbyConnectionError: Connection failed
            EmbyTimeoutError: Request timeout
            EmbyAPIError: Other API errors
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "X-Emby-Token": self.api_key,
            "Accept": "application/json",
        }

        _LOGGER.debug("Making %s request to %s", method, endpoint)

        try:
            async with async_timeout.timeout(timeout):
                async with self.session.request(
                    method,
                    url,
                    headers=headers,
                    json=data,
                    params=params,
                    ssl=False,  # Allow self-signed certs
                ) as response:
                    _LOGGER.debug("Response status: %s", response.status)

                    if response.status == 401:
                        raise EmbyAuthError(ERROR_AUTH)

                    if response.status == 404:
                        _LOGGER.warning("Endpoint not found: %s", endpoint)
                        return None

                    response.raise_for_status()

                    # Parse response
                    if response.content_type == "application/json":
                        return await response.json()

                    return await response.text()

        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout connecting to Emby at %s", url)
            raise EmbyTimeoutError(ERROR_TIMEOUT) from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Emby: %s", err)
            raise EmbyConnectionError(ERROR_CONNECT) from err
        except EmbyAuthError:
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            raise EmbyAPIError(ERROR_UNKNOWN) from err

    async def get_system_info(self) -> dict[str, Any]:
        """Get complete system information.

        Returns:
            System information dict with keys:
                - ServerName
                - Version
                - Id
                - OperatingSystem
                - HasPendingRestart
                - WebSocketPortNumber
                - HttpServerPortNumber
                etc.
        """
        return await self._request("GET", API_ENDPOINT_SYSTEM_INFO)

    async def get_system_info_public(self) -> dict[str, Any]:
        """Get public system information.

        Returns:
            Public system info dict with keys:
                - ServerName
                - Version
                - Id
        """
        return await self._request("GET", API_ENDPOINT_SYSTEM_INFO_PUBLIC)

    async def get_system_endpoint(self) -> dict[str, Any]:
        """Get system endpoint information.

        Returns:
            Endpoint info dict with keys:
                - IsLocal
                - IsInNetwork
        """
        return await self._request("GET", API_ENDPOINT_SYSTEM_ENDPOINT)

    async def get_items_counts(self) -> dict[str, Any]:
        """Get media item counts.

        Returns:
            Item counts dict with keys:
                - MovieCount
                - SeriesCount
                - EpisodeCount
                - GameCount
                - ArtistCount
                - SongCount
                - AlbumCount
                etc.
        """
        return await self._request("GET", API_ENDPOINT_ITEMS_COUNTS)

    async def get_library_folders(self) -> dict[str, Any]:
        """Get library media folders.

        Returns:
            Dict with 'Items' key containing list of folder objects:
                - Name
                - Id
                - Type
                - DateCreated
                etc.
        """
        return await self._request("GET", API_ENDPOINT_LIBRARY_FOLDERS)

    async def get_sessions(self) -> list[dict[str, Any]]:
        """Get active sessions.

        Returns:
            List of session dicts with keys:
                - Id
                - Client
                - DeviceName
                - UserName
                - PlayState
                - NowPlayingItem
                - LastActivityDate
                etc.
        """
        return await self._request("GET", API_ENDPOINT_SESSIONS)

    async def get_users(self) -> list[dict[str, Any]]:
        """Get all users.

        Returns:
            List of user dicts with keys:
                - Name
                - Id
                - HasPassword
                - LastLoginDate
                - LastActivityDate
                - Configuration
                etc.
        """
        return await self._request("GET", API_ENDPOINT_USERS)

    async def get_activity_log(self, limit: int = 10) -> dict[str, Any]:
        """Get activity log entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            Dict with 'Items' key containing list of activity objects:
                - Id
                - Name
                - Type
                - Date
                - UserId
                - Severity
                etc.
        """
        params = {"limit": limit}
        return await self._request("GET", API_ENDPOINT_ACTIVITY_LOG, params=params)

    async def get_scheduled_tasks(self) -> list[dict[str, Any]]:
        """Get scheduled tasks.

        Returns:
            List of task dicts with keys:
                - Name
                - State
                - Id
                - LastExecutionResult
                - Triggers
                - Description
                - Category
                etc.
        """
        return await self._request("GET", API_ENDPOINT_SCHEDULED_TASKS)

    async def get_devices(self) -> dict[str, Any]:
        """Get connected devices.

        Returns:
            Dict with 'Items' key containing list of device objects:
                - Name
                - Id
                - ReportedDeviceId
                - LastUserName
                - AppName
                - AppVersion
                - DateLastActivity
                - IpAddress
                etc.
        """
        return await self._request("GET", API_ENDPOINT_DEVICES)

    async def get_dashboard_overview(self) -> dict[str, Any]:
        """Get complete dashboard data with concurrent requests.

        Makes parallel requests to all API endpoints for efficient data gathering.

        Returns:
            Dict containing all dashboard data:
                - system_info: System information
                - endpoint_info: Endpoint information
                - items_counts: Media counts
                - library_folders: Library folders
                - sessions: Active sessions
                - users: User list
                - activity_log: Recent activities
                - scheduled_tasks: Scheduled tasks
                - devices: Connected devices
        """
        _LOGGER.debug("Fetching dashboard overview (9 concurrent requests)")

        # Execute all requests concurrently for better performance
        results = await asyncio.gather(
            self.get_system_info(),
            self.get_system_endpoint(),
            self.get_items_counts(),
            self.get_library_folders(),
            self.get_sessions(),
            self.get_users(),
            self.get_activity_log(10),
            self.get_scheduled_tasks(),
            self.get_devices(),
            return_exceptions=True,
        )

        # Process results with graceful degradation
        system_info = results[0] if not isinstance(results[0], Exception) else {}
        endpoint_info = results[1] if not isinstance(results[1], Exception) else {}
        items_counts = results[2] if not isinstance(results[2], Exception) else {}
        library_folders = results[3] if not isinstance(results[3], Exception) else {}
        sessions = results[4] if not isinstance(results[4], Exception) else []
        users = results[5] if not isinstance(results[5], Exception) else []
        activity_log = results[6] if not isinstance(results[6], Exception) else {}
        scheduled_tasks = results[7] if not isinstance(results[7], Exception) else []
        devices = results[8] if not isinstance(results[8], Exception) else {}

        # Log any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                _LOGGER.warning("Request %d failed: %s", i, result)

        return {
            "system_info": system_info,
            "endpoint_info": endpoint_info,
            "items_counts": items_counts,
            "library_folders": library_folders,
            "sessions": sessions,
            "users": users,
            "activity_log": activity_log,
            "scheduled_tasks": scheduled_tasks,
            "devices": devices,
        }

    async def test_connection(self) -> bool:
        """Test the connection to Emby server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            info = await self.get_system_info_public()
            return info is not None and "ServerName" in info
        except Exception as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False
