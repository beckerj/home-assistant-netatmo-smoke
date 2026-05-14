import logging
import time

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ALARM_CLEAR_TIMEOUT_SECONDS

_LOGGER = logging.getLogger(__name__)

# Event types that indicate an active alarm
ALARM_EVENT_TYPES = {"smoke", "sds_alarm"}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NetatmoSmokeDetected(coordinator, module_id)
        for module_id in coordinator.data
    )


class NetatmoSmokeDetected(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor: smoke alarm state based on last event."""

    _attr_device_class = "smoke"

    def __init__(self, coordinator, module_id):
        super().__init__(coordinator)
        self._module_id = module_id
        self._attr_unique_id = f"{module_id}_smoke"

    @property
    def _module(self):
        return self.coordinator.data.get(self._module_id, {})

    @property
    def name(self):
        return f"{self._module.get('name', self._module_id)} Smoke Detected"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._module_id)},
            "name": self._module.get("name", self._module_id),
            "manufacturer": "Netatmo",
            "model": "Smart Smoke Detector",
        }

    @property
    def is_on(self):
        ev_type = self._module.get("last_event_type", "")
        if ev_type not in ALARM_EVENT_TYPES:
            return False

        ev_time = self._module.get("last_event_time")
        if not ev_time:
            return True

        # Clear alarm after timeout since no explicit "all clear" event exists
        return (time.time() - ev_time) < ALARM_CLEAR_TIMEOUT_SECONDS

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._module.get("last_event_time"):
            attrs["last_event_time"] = self._module["last_event_time"]
        if self._module.get("last_event_type"):
            attrs["last_event_type"] = self._module["last_event_type"]
        if self._module.get("last_event_message"):
            attrs["last_event_message"] = self._module["last_event_message"]
        return attrs
