import logging
from datetime import timedelta

import aiohttp

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NetatmoHomeAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class NetatmoSmokeCoordinator(DataUpdateCoordinator):
    """Coordinator that polls Netatmo gethomedata + homestatus for NSD modules."""

    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        session = async_get_clientsession(hass)
        self.api = NetatmoHomeAPI(
            entry.data["client_id"],
            entry.data["client_secret"],
            entry.data["refresh_token"],
            session,
        )
        self._entry = entry

    async def _async_update_data(self):
        """Fetch data from the Netatmo API."""
        try:
            modules = await self.api.get_smoke_data()
        except (aiohttp.ClientError, KeyError) as err:
            raise UpdateFailed(f"Error communicating with Netatmo API: {err}") from err

        # Persist the (possibly rotated) refresh token
        new_token = self.api.refresh_token
        if new_token != self._entry.data.get("refresh_token"):
            self.hass.config_entries.async_update_entry(
                self._entry,
                data={**self._entry.data, "refresh_token": new_token},
            )

        _LOGGER.info("Found %d smoke detector modules", len(modules))
        for m in modules:
            _LOGGER.debug("Module %s: %s", m["id"], m)

        return {m["id"]: m for m in modules}
