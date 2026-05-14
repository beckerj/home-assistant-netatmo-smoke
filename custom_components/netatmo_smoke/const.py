DOMAIN = "netatmo_smoke"

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_REFRESH_TOKEN = "refresh_token"

API_BASE = "https://api.netatmo.com/api"

# Netatmo does not send an explicit "all clear" event.
# After this many seconds the binary sensor resets to off.
ALARM_CLEAR_TIMEOUT_SECONDS = 3600
