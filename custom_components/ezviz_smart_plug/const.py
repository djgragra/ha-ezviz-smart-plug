"""Constants for the EZVIZ Smart Plug integration."""

from datetime import timedelta

DOMAIN = "ezviz_smart_plug"
MANUFACTURER = "EZVIZ"

# Config entry data keys (the account password is never stored, only the tokens).
CONF_SESSION_ID = "session_id"
CONF_RFSESSION_ID = "rf_session_id"

EU_URL = "apiieu.ezvizlife.com"

DEFAULT_TIMEOUT = 25
UPDATE_INTERVAL = timedelta(seconds=30)

# deviceInfos.status value reported by the cloud for an offline device.
STATUS_OFFLINE = 2
