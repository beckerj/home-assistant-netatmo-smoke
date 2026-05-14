# Netatmo Smoke Detectors (Home API)

Custom Home Assistant integration for Netatmo Smart Smoke Detectors (NSD) using the Netatmo Security/Home API.

## Why this integration?

The official Netatmo integration in Home Assistant only exposes smoke detectors as camera-related devices with limited functionality. This custom integration provides dedicated sensors for each smoke detector with data that's actually available from the Netatmo API.

## What data is available?

The Netatmo API for NSD modules provides:

| Data | Source | Sensor |
|---|---|---|
| WiFi signal strength (dBm) | homestatus | WiFi Signal |
| Firmware revision | homestatus | Firmware |
| Last seen timestamp | homestatus | Last Seen |
| Last event type & message | gethomedata | Last Event |
| Smoke alarm state | gethomedata events | Smoke Detected (binary) |

**Note:** The Netatmo API does **not** expose battery percentage, temperature, or real-time smoke detection status for NSD modules. Battery and temperature fields are not available in the `gethomedata` or `homestatus` endpoints.

## Entities per smoke detector

Each detector creates 5 entities:

- **Binary Sensor:** Smoke Detected (on when last event type is `smoke` or `sds_alarm`; automatically clears to `off` after 1 hour since Netatmo does not send an explicit "all clear" event)
- **Sensor:** WiFi Signal (dBm, signal_strength device class)
- **Sensor:** Firmware (software version number)
- **Sensor:** Last Seen (timestamp when last seen online)
- **Sensor:** Last Event (event type with message as attribute)

## Installation

1. Copy the `netatmo_smoke/` folder to `/config/custom_components/netatmo_smoke/` on your Home Assistant instance
2. Restart Home Assistant
3. Go to **Settings** > **Integrations** > **Add Integration**
4. Search for "Netatmo Smoke Detectors"

## Setup

You need Netatmo API credentials:

1. Go to [https://dev.netatmo.com](https://dev.netatmo.com) and create an app
2. Note your **Client ID** and **Client Secret**
3. Generate a **Refresh Token** (use the app's OAuth2 flow with the `read_camera` scope)
4. Enter these three values in the config flow

The required OAuth scope is `read_camera` (Security API access for smoke detectors).

## API endpoints used

| Endpoint | Purpose |
|---|---|
| `POST /oauth2/token` | OAuth2 token refresh (rotates refresh token) |
| `GET /api/gethomedata` | Smoke detector names, setup dates, and events |
| `GET /api/homestatus` | Firmware, last_seen, wifi_strength |

Data is polled every 5 minutes. The refresh token is automatically persisted back to the config entry when Netatmo rotates it.

## Known Limitations

### Refresh Token Race Condition

Netatmo rotates the refresh token on every OAuth2 token refresh. The integration persists the new token immediately after a successful API call via `async_update_entry`. However, there is a **non-atomic window** between receiving the new token from Netatmo and writing it to Home Assistant's config entry storage.

If Home Assistant crashes or restarts in this exact window, the next startup will use the stale (revoked) refresh token. You will need to re-authorise the integration and generate a new refresh token.

**Mitigation**: The integration refreshes the token at the start of every data update, and writes it back immediately. The window is typically milliseconds long. There is no transactional/atomic write primitive available in the Home Assistant Config Entries API, so this is the safest implementation possible.

### Rate Limiting

Netatmo's API limits are **50 requests / 10 seconds** and **500 requests / hour** per user per app. The integration makes 2–3 calls every 5 minutes (~36/hour), well within the limit.

However, Netatmo also applies a global WAF that can return HTTP 429 independently of your personal quota. The integration handles this automatically: it parses the `Retry-After` header (capped at 60 seconds) and waits before retrying (max 3 attempts).

## File structure

```
netatmo_smoke/
├── __init__.py          # Config entry setup/teardown
├── manifest.json        # Integration metadata
├── config_flow.py       # UI config flow (client_id, client_secret, refresh_token)
├── api.py               # Netatmo API client (OAuth2 + two endpoints)
├── coordinator.py       # DataUpdateCoordinator (5-min poll cycle)
├── binary_sensor.py     # Smoke detected binary sensor
├── sensor.py            # WiFi, firmware, last_seen, last_event sensors
├── const.py             # Domain and config constants
└── strings.json         # Translations for config flow errors
```