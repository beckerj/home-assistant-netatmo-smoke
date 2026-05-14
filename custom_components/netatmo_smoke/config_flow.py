import voluptuous as vol
import aiohttp
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_REFRESH_TOKEN
from .api import NetatmoHomeAPI


class NetatmoSmokeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Netatmo Smoke Detectors."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            client_id = user_input[CONF_CLIENT_ID].strip()
            client_secret = user_input[CONF_CLIENT_SECRET].strip()
            refresh_token = user_input[CONF_REFRESH_TOKEN].strip()

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
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
