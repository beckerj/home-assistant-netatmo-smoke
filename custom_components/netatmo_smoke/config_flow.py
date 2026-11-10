import voluptuous as vol
import aiohttp
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL_MINUTES,
    MIN_POLL_INTERVAL_MINUTES,
    MAX_POLL_INTERVAL_MINUTES,
)
from .api import NetatmoHomeAPI


POLL_INTERVAL_VALIDATOR = vol.All(
    vol.Coerce(int),
    vol.Range(min=MIN_POLL_INTERVAL_MINUTES, max=MAX_POLL_INTERVAL_MINUTES),
)


def _get_poll_interval(entry) -> int:
    """Read the poll interval: options first, then config data, then default."""
    return entry.options.get(
        CONF_POLL_INTERVAL,
        entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL_MINUTES),
    )


class NetatmoSmokeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Netatmo Smoke Detectors."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            client_id = user_input[CONF_CLIENT_ID].strip()
            client_secret = user_input[CONF_CLIENT_SECRET].strip()
            refresh_token = user_input[CONF_REFRESH_TOKEN].strip()
            poll_interval = user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL_MINUTES)

            if not all([client_id, client_secret, refresh_token]):
                errors["base"] = "missing_data"
            else:
                session = async_get_clientsession(self.hass)
                api = NetatmoHomeAPI(client_id, client_secret, refresh_token, session)
                try:
                    modules = await api.get_smoke_data()
                    if not modules:
                        errors["base"] = "no_modules"
                    else:
                        return self.async_create_entry(
                            title="Netatmo Smoke Detectors",
                            data={
                                CONF_CLIENT_ID: client_id,
                                CONF_CLIENT_SECRET: client_secret,
                                CONF_REFRESH_TOKEN: refresh_token,
                                CONF_POLL_INTERVAL: poll_interval,
                            },
                        )
                except aiohttp.ClientResponseError as err:
                    if err.status == 401:
                        errors["base"] = "invalid_auth"
                    else:
                        errors["base"] = "cannot_connect"
                except (aiohttp.ClientError, KeyError):
                    errors["base"] = "cannot_connect"

        schema = vol.Schema({
            vol.Required(CONF_CLIENT_ID): str,
            vol.Required(CONF_CLIENT_SECRET): str,
            vol.Required(CONF_REFRESH_TOKEN): str,
            vol.Optional(
                CONF_POLL_INTERVAL,
                default=DEFAULT_POLL_INTERVAL_MINUTES,
                description="Poll interval in minutes",
            ): POLL_INTERVAL_VALIDATOR,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(entry):
        return NetatmoSmokeOptionsFlowHandler(entry)


class NetatmoSmokeOptionsFlowHandler(config_entries.OptionsFlow):
    """Allow changing the poll interval without re-entering credentials.

    Netatmo plans to reduce polling rate limits from March 2027; this flow
    is the knob for adapting to the announced limits.
    """

    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Required(
                CONF_POLL_INTERVAL,
                default=_get_poll_interval(self.entry),
            ): POLL_INTERVAL_VALIDATOR,
        })

        return self.async_show_form(step_id="init", data_schema=schema)
