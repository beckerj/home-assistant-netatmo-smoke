DOMAIN = "netatmo_smoke"

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_REFRESH_TOKEN = "refresh_token"

# Poll interval in minutes, configurable via the config flow and later
# through the integration's Options. Netatmo plans to reduce API rate
# limits for polling-based integrations from March 2027 — raise this
# value if the new limits no longer fit a 5-minute cycle.
CONF_POLL_INTERVAL = "poll_interval"
DEFAULT_POLL_INTERVAL_MINUTES = 5
MIN_POLL_INTERVAL_MINUTES = 1
MAX_POLL_INTERVAL_MINUTES = 1440

API_BASE = "https://api.netatmo.com/api"

# Netatmo does not send an explicit "all clear" event.
# After this many seconds the binary sensor resets to off.
ALARM_CLEAR_TIMEOUT_SECONDS = 3600
