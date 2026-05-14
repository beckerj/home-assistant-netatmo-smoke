import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

_RETRY_AFTER_MAX_SECONDS = 60


class NetatmoHomeAPI:
    """Async Netatmo Security/Home API client using OAuth2 refresh-token flow.

    Uses two endpoints:
      - gethomedata  — module names, setup dates, recent events
      - homestatus   — firmware, last_seen, wifi_strength
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        session: aiohttp.ClientSession,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token: str | None = None
        self._home_id: str | None = None
        self._session = session

    async def refresh(self) -> None:
        """Refresh the OAuth2 access token."""
        async with self._session.post(
            "https://api.netatmo.com/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        ) as response:
            response.raise_for_status()
            data = await response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]

    @staticmethod
    def _parse_retry_after(header_value: str) -> float:
        """Parse Retry-After header as seconds (int) or HTTP-date."""
        try:
            return min(float(header_value), _RETRY_AFTER_MAX_SECONDS)
        except ValueError:
            pass
        try:
            import email.utils
            dt = email.utils.parsedate_to_datetime(header_value)
            delay = (dt - datetime.now(timezone.utc)).total_seconds()
            return min(max(delay, 0), _RETRY_AFTER_MAX_SECONDS)
        except Exception:
            return 5.0

    async def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> dict:
        """Execute HTTP request with automatic retry on 5xx and token refresh on 401."""
        max_retries = 3

        for attempt in range(max_retries):
            if not self.access_token:
                await self.refresh()

            headers = kwargs.pop("headers", {})
            headers["Authorization"] = f"Bearer {self.access_token}"

            try:
                async with self._session.request(
                    method, url, headers=headers, **kwargs
                ) as response:
                    if response.status == 401 and attempt < max_retries - 1:
                        await self.refresh()
                        continue

                    if response.status == 429 and attempt < max_retries - 1:
                        retry_after = response.headers.get("Retry-After", "5")
                        delay = self._parse_retry_after(retry_after)
                        _LOGGER.warning(
                            "Netatmo API rate limited (429), waiting %.1fs then retrying (%d/%d)",
                            delay,
                            attempt + 1,
                            max_retries,
                        )
                        await asyncio.sleep(delay)
                        continue

                    if 500 <= response.status < 600 and attempt < max_retries - 1:
                        _LOGGER.warning(
                            "Netatmo API returned %d, retrying (%d/%d)",
                            response.status,
                            attempt + 1,
                            max_retries,
                        )
                        continue

                    response.raise_for_status()
                    return await response.json()

            except aiohttp.ClientError as err:
                if attempt < max_retries - 1:
                    _LOGGER.warning(
                        "Netatmo API request failed: %s, retrying (%d/%d)",
                        err,
                        attempt + 1,
                        max_retries,
                    )
                    continue
                raise

        raise aiohttp.ClientError("Max retries exceeded")

    async def _get(self, url: str) -> dict:
        """GET with automatic token refresh on 401."""
        return await self._request_with_retry("GET", url)

    async def get_smoke_data(self) -> list[dict]:
        """Fetch and merge smoke-detector data from both APIs.

        Returns a list of dicts, one per NSD module, with keys:
          id, name, type, firmware_revision, last_seen, wifi_strength,
          last_event_type, last_event_time, last_event_message
        """
        # --- gethomedata: names, events ---
        home_data = await self._get("https://api.netatmo.com/api/gethomedata")
        body = home_data.get("body", {})
        homes = body.get("homes", [])
        if not homes:
            _LOGGER.warning("Netatmo API returned no homes")
            return []
        home = homes[0]
        self._home_id = home.get("id")
        if not self._home_id:
            _LOGGER.warning("Netatmo API returned a home without an id")
            return []

        modules_by_id: dict[str, dict] = {}
        for sd in home.get("smokedetectors", []):
            modules_by_id[sd["id"]] = {
                "id": sd["id"],
                "name": sd.get("name", sd["id"]),
                "type": "NSD",
                "last_setup": sd.get("last_setup"),
            }

        # Index latest event per device
        latest_event: dict[str, dict] = {}
        for ev in home.get("events", []):
            dev_id = ev.get("device_id")
            if dev_id in modules_by_id:
                if dev_id not in latest_event or ev.get("time", 0) > latest_event[dev_id].get("time", 0):
                    latest_event[dev_id] = ev

        # --- homestatus: firmware, wifi, last_seen ---
        status_data = await self._get(
            f"https://api.netatmo.com/api/homestatus?home_id={self._home_id}"
        )
        for mod in status_data.get("body", {}).get("home", {}).get("modules", []):
            if mod.get("type") == "NSD" and mod["id"] in modules_by_id:
                modules_by_id[mod["id"]].update({
                    "firmware_revision": mod.get("firmware_revision"),
                    "last_seen": mod.get("last_seen"),
                    "wifi_strength": mod.get("wifi_strength"),
                })

        # Merge latest events
        for dev_id, ev in latest_event.items():
            modules_by_id[dev_id]["last_event_type"] = ev.get("type")
            modules_by_id[dev_id]["last_event_time"] = ev.get("time")
            modules_by_id[dev_id]["last_event_message"] = ev.get("message")

        return list(modules_by_id.values())
