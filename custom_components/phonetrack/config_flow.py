"""Config flow for phonetrack component."""
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_DEVICES, CONF_TOKEN, CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import requests

from .const import (
    CONF_MAX_GPS_ACCURACY,
    CONF_NAME,
    CONF_RECONNECT_INTERVAL,
    CONF_UPDATE_TIME_MINUTES,
    CONF_UPDATE_TIME_SECONDS,
    CONF_VERIFY_SSL,
    DEFAULT_MAX_GPS_ACCURACY,
    DEFAULT_NAME,
    DEFAULT_RECONNECT_INTERVAL,
    DEFAULT_UPDATE_TIME_MINUTES,
    DEFAULT_UPDATE_TIME_SECONDS,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=""): str,
        vol.Required(CONF_URL): str,
        vol.Required(CONF_TOKEN): str,
        vol.Optional(
            CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL
        ): bool,
        vol.Optional(
            CONF_RECONNECT_INTERVAL, default=DEFAULT_RECONNECT_INTERVAL
        ): vol.Coerce(int),
        vol.Optional(
            CONF_UPDATE_TIME_MINUTES, default=DEFAULT_UPDATE_TIME_MINUTES
        ): vol.Coerce(int),
        vol.Optional(
            CONF_UPDATE_TIME_SECONDS, default=DEFAULT_UPDATE_TIME_SECONDS
        ): vol.Coerce(int),
        vol.Optional(
            CONF_MAX_GPS_ACCURACY, default=DEFAULT_MAX_GPS_ACCURACY
        ): vol.Coerce(float),
    }
)


async def async_test_url(hass: HomeAssistant, url: str, token: str, verify_ssl: bool) -> tuple[bool, str]:
    """Test a URL and return (success, actual_url)."""
    try:
        url_full = f"{url}/{token}"
        _LOGGER.debug("Testing URL: %s", url_full)
        response = await hass.async_add_executor_job(
            requests.get, url_full, {"timeout": 10, "verify": verify_ssl}
        )
        response.raise_for_status()
        data = response.json()
        if token in data:
            _LOGGER.debug("Successfully connected to URL: %s", url)
            return True, url
        return False, f"Token not found in response for {url}"
    except requests.exceptions.RequestException as err:
        _LOGGER.debug("Failed to connect to %s: %s", url, err)
        return False, str(err)
    except ValueError as err:
        _LOGGER.debug("Invalid JSON response from %s: %s", url, err)
        return False, str(err)


async def async_test_url_with_fallback(hass: HomeAssistant, base_url: str, token: str, verify_ssl: bool) -> tuple[bool, str, str]:
    """Try multiple URL formats and return (success, actual_url, error_message)."""
    _LOGGER.debug("Testing URL with fallback for base: %s", base_url)
    
    # If URL already looks complete, just test it
    if base_url.endswith("/"):
        base_url = base_url.rstrip("/")
    
    # Build variations
    url_variants = []
    path_variants = [
        "/index.php/apps/phonetrack/api/getlastpositions",
        "/apps/phonetrack/api/getlastpositions",
        "/index.php/apps/phonetrack/api/getlastpositions/",
        "/apps/phonetrack/api/getlastpositions/",
    ]
    
    for path in path_variants:
        url_variants.append(f"https://{base_url}{path}")
        url_variants.append(f"http://{base_url}{path}")
    
    # Also try the base URL with token appended directly
    url_variants.append(f"https://{base_url}/{token}")
    url_variants.append(f"http://{base_url}/{token}")
    
    # If it looks like a full URL, try it as-is first
    if base_url.startswith(("http://", "https://")):
        url_variants.insert(0, base_url)
    
    # Remove duplicates while preserving order
    seen = set()
    url_variants = [u for u in url_variants if not (u in seen or seen.add(u))]
    
    _LOGGER.debug("URL variants to try: %s", url_variants)
    
    for url in url_variants:
        success, result = await async_test_url(hass, url, token, verify_ssl)
        if success:
            _LOGGER.info("Successfully connected using URL: %s", url)
            return True, url, ""
    
    # If we get here, all attempts failed
    error_msg = result if not url_variants else f"Could not connect with any URL variant"
    _LOGGER.error("All URL attempts failed: %s", error_msg)
    return False, "", error_msg


async def async_get_available_devices(hass: HomeAssistant, url: str, token: str, verify_ssl: bool = True) -> list[str]:
    """Get available devices from the PhoneTrack server."""
    _LOGGER.debug("Fetching devices from %s with verify_ssl=%s", url, verify_ssl)
    try:
        url_full = f"{url}/{token}"
        response = await hass.async_add_executor_job(
            requests.get, url_full, {"timeout": 10, "verify": verify_ssl}
        )
        response.raise_for_status()
        data = response.json()
        
        # Get devices from the response - data[token] is a dict with device names as keys
        if token in data:
            _LOGGER.debug("Found %d devices", len(data[token].keys()))
            return list(data[token].keys())
        _LOGGER.warning("Token %s not found in server response", token)
        return []
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Could not fetch devices: %s", err)
        return []


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    url = data[CONF_URL]
    token = data[CONF_TOKEN]
    verify_ssl = data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    _LOGGER.debug("validate_input with url=%s, verify_ssl=%s", url, verify_ssl)

    # Test connection to PhoneTrack server with URL fallback
    success, actual_url, error_msg = await async_test_url_with_fallback(
        hass, url, token, verify_ssl
    )
    
    if not success:
        _LOGGER.error("Connection test failed: %s", error_msg)
        raise CannotConnect(error_msg)

    _LOGGER.info("Successfully connected to PhoneTrack at %s", actual_url)
    
    # Return the actual working URL
    return {"title": data.get(CONF_NAME, actual_url).strip() or actual_url, "actual_url": actual_url}


class PhoneTrackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PhoneTrack."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        _LOGGER.debug("async_step_user called with user_input: %s", user_input)
        errors = {}

        if user_input is not None:
            try:
                _LOGGER.debug("Validating input...")
                info = await validate_input(self.hass, user_input)
                _LOGGER.debug("Input validated: %s", info)
                
                _LOGGER.debug("Fetching available devices...")
                devices = await async_get_available_devices(
                    self.hass, info.get("actual_url", user_input[CONF_URL]), user_input[CONF_TOKEN], user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
                )
                _LOGGER.debug("Available devices: %s", devices)
            except CannotConnect as err:
                _LOGGER.error("Cannot connect to PhoneTrack server: %s", err)
                errors["base"] = "cannot_connect"
            except InvalidUrl as err:
                _LOGGER.error("Invalid URL: %s", err)
                errors["base"] = "invalid_url"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception(
                    "Unexpected error during configuration: %s", err
                )
                errors["base"] = "unknown"
            else:
                # Store devices as a list
                user_input[CONF_DEVICES] = devices
                user_input[CONF_NAME] = info["title"]
                user_input[CONF_URL] = info.get("actual_url", user_input[CONF_URL])
                _LOGGER.info(
                    "Configuration successful. URL: %s, Devices: %s, Name: %s",
                    user_input[CONF_URL],
                    devices,
                    info["title"],
                )
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        _LOGGER.debug("Showing form with errors: %s", errors)
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        _LOGGER.debug("async_step_reconfigure called with user_input: %s", user_input)
        
        # Get entry_id from the context
        entry_id = self.context.get("entry_id")
        _LOGGER.debug("Entry ID from context: %s", entry_id)
        
        if entry_id is None:
            _LOGGER.error("No entry_id provided for reconfigure")
            return self.async_abort(reason="no_entry_id")
        
        reconfigure_entry = self.hass.config_entries.async_get_entry(entry_id)
        if reconfigure_entry is None:
            _LOGGER.error("Entry not found for reconfigure: %s", entry_id)
            return self.async_abort(reason="entry_not_found")
        
        _LOGGER.debug("Reconfigure entry data: %s", reconfigure_entry.data)

        errors = {}
        if user_input is not None:
            try:
                _LOGGER.debug("Validating reconfiguration input...")
                info = await validate_input(self.hass, user_input)
                _LOGGER.debug("Reconfiguration input validated: %s", info)
                
                _LOGGER.debug("Fetching available devices for reconfiguration...")
                devices = await async_get_available_devices(
                    self.hass, info.get("actual_url", user_input[CONF_URL]), user_input[CONF_TOKEN], user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
                )
                _LOGGER.debug("Available devices: %s", devices)
            except CannotConnect as err:
                _LOGGER.error("Cannot connect to PhoneTrack server during reconfigure: %s", err)
                errors["base"] = "cannot_connect"
            except InvalidUrl as err:
                _LOGGER.error("Invalid URL during reconfiguration: %s", err)
                errors["base"] = "invalid_url"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception(
                    "Unexpected error during reconfiguration: %s", err
                )
                errors["base"] = "unknown"
            else:
                # Store devices as a list
                user_input[CONF_DEVICES] = devices
                user_input[CONF_URL] = info.get("actual_url", user_input[CONF_URL])
                _LOGGER.info(
                    "Reconfiguration successful. URL: %s, Devices: %s",
                    user_input[CONF_URL],
                    devices,
                )
                self.hass.config_entries.async_update_entry(
                    reconfigure_entry,
                    data=user_input,
                )
                return self.async_abort(
                    reason="reconfigure_successful",
                    description_placeholders={"name": reconfigure_entry.title},
                )

        # Pre-populate with existing values - use the main DATA_SCHEMA with defaults
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NAME, default=reconfigure_entry.data.get(CONF_NAME, DEFAULT_NAME)
                ): str,
                vol.Required(
                    CONF_URL, default=reconfigure_entry.data.get(CONF_URL, "")
                ): str,
                vol.Required(
                    CONF_TOKEN, default=reconfigure_entry.data.get(CONF_TOKEN, "")
                ): str,
                vol.Optional(
                    CONF_VERIFY_SSL,
                    default=reconfigure_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                ): bool,
                vol.Optional(
                    CONF_RECONNECT_INTERVAL,
                    default=reconfigure_entry.data.get(CONF_RECONNECT_INTERVAL, DEFAULT_RECONNECT_INTERVAL),
                ): int,
                vol.Optional(
                    CONF_UPDATE_TIME_MINUTES,
                    default=reconfigure_entry.data.get(CONF_UPDATE_TIME_MINUTES, DEFAULT_UPDATE_TIME_MINUTES),
                ): int,
                vol.Optional(
                    CONF_UPDATE_TIME_SECONDS,
                    default=reconfigure_entry.data.get(CONF_UPDATE_TIME_SECONDS, DEFAULT_UPDATE_TIME_SECONDS),
                ): int,
                vol.Optional(
                    CONF_MAX_GPS_ACCURACY,
                    default=reconfigure_entry.data.get(CONF_MAX_GPS_ACCURACY, DEFAULT_MAX_GPS_ACCURACY),
                ): float,
            }
        )

        _LOGGER.debug("Showing reconfigure form with errors: %s", errors)
        return self.async_show_form(
            step_id="reconfigure", data_schema=data_schema, errors=errors
        )


class CannotConnect(Exception):
    """Exception raised when we cannot connect to the PhoneTrack server."""


class InvalidUrl(Exception):
    """Exception raised when the URL is invalid."""
