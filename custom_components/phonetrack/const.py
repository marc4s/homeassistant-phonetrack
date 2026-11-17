"""Constants for phonetrack component."""
from datetime import timedelta

# Domain and configuration keys
DOMAIN = "phonetrack"

CONF_DEVICES = "devices"
CONF_TOKEN = "token"
CONF_URL = "url"
CONF_MAX_GPS_ACCURACY = "max_gps_accuracy"
CONF_UPDATE_TIME_MINUTES = "update_time_minutes"
CONF_UPDATE_TIME_SECONDS = "update_time_seconds"
CONF_RECONNECT_INTERVAL = "reconnect_interval"

# Default values
DEFAULT_UPDATE_TIME_MINUTES = 5
DEFAULT_UPDATE_TIME_SECONDS = 0
DEFAULT_MAX_GPS_ACCURACY = 100000
DEFAULT_RECONNECT_INTERVAL = 300  # seconds

# Update intervals
MIN_UPDATE_INTERVAL = timedelta(seconds=30)  # Minimum 30 seconds
