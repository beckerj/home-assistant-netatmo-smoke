import logging
from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for module_id in coordinator.data:
        entities.append(NetatmoWifi(coordinator, module_id))
        entities.append(NetatmoFirmware(coordinator, module_id))
        entities.append(NetatmoLastSeen(coordinator, module_id))
        entities.append(NetatmoLastEvent(coordinator, module_id))
    async_add_entities(entities)


class BaseNetatmoSensor(CoordinatorEntity, SensorEntity):
    """Base class for Netatmo smoke-detector sensors."""

    def __init__(self, coordinator, module_id, uid_suffix: str):
        super().__init__(coordinator)
        self._module_id = module_id
        self._uid_suffix = uid_suffix
        self._attr_unique_id = f"{module_id}_{uid_suffix}"

    @property
    def _module(self):
        return self.coordinator.data.get(self._module_id, {})

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._module_id)},
            "name": self._module.get("name", self._module_id),
            "manufacturer": "Netatmo",
            "model": "Smart Smoke Detector",
        }


class NetatmoWifi(BaseNetatmoSensor):
    _attr_device_class = "signal_strength"
    _attr_native_unit_of_measurement = "dBm"
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator, module_id):
        super().__init__(coordinator, module_id, "wifi")
        self._attr_name = f"{coordinator.data[module_id].get('name', module_id)} WiFi Signal"

    @property
    def native_value(self):
        return self._module.get("wifi_strength")


class NetatmoFirmware(BaseNetatmoSensor):
    _attr_icon = "mdi:chip"

    def __init__(self, coordinator, module_id):
        super().__init__(coordinator, module_id, "firmware")
        self._attr_name = f"{coordinator.data[module_id].get('name', module_id)} Firmware"

    @property
    def native_value(self):
        fw = self._module.get("firmware_revision")
        return str(fw) if fw is not None else None


class NetatmoLastSeen(BaseNetatmoSensor):
    _attr_device_class = "timestamp"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator, module_id):
        super().__init__(coordinator, module_id, "last_seen")
        self._attr_name = f"{coordinator.data[module_id].get('name', module_id)} Last Seen"

    @property
    def native_value(self):
        ts = self._module.get("last_seen")
        if ts:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        return None


class NetatmoLastEvent(BaseNetatmoSensor):
    _attr_icon = "mdi:bell-outline"

    def __init__(self, coordinator, module_id):
        super().__init__(coordinator, module_id, "last_event")
        self._attr_name = f"{coordinator.data[module_id].get('name', module_id)} Last Event"

    @property
    def native_value(self):
        return self._module.get("last_event_type")

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._module.get("last_event_time"):
            attrs["event_time"] = datetime.fromtimestamp(self._module["last_event_time"], tz=timezone.utc).isoformat()
        if self._module.get("last_event_message"):
            attrs["message"] = self._module["last_event_message"]
        return attrs