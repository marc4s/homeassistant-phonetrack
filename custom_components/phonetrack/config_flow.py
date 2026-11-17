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
    CONF_RECONNECT_INTERVAL,
    CONF_UPDATE_TIME_MINUTES,
    CONF_UPDATE_TIME_SECONDS,
    DEFAULT_MAX_GPS_ACCURACY,
    DEFAULT_RECONNECT_INTERVAL,
    DEFAULT_UPDATE_TIME_MINUTES,
    DEFAULT_UPDATE_TIME_SECONDS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_TOKEN): str,
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


async def async_get_available_devices(hass: HomeAssistant, url: str, token: str) -> list[str]:
    """Get available devices from the PhoneTrack server."""
    try:
        url_full = f"{url}/{token}"
        response = await hass.async_add_executor_job(
            requests.get, url_full, {"timeout": 10}
        )
        response.raise_for_status()
        data = response.json()
        
        # Get devices from the response - data[token] is a dict with device names as keys
        if token in data:
            return list(data[token].keys())
        return []
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.warning("Could not fetch devices: %s", err)
        return []


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # Validate the URL format
    if not data[CONF_URL].startswith(("http://", "https://")):
        raise InvalidUrl

    # Test connection to PhoneTrack server
    try:
        # Create a test request to verify connection
        url = f"{data[CONF_URL]}/{data[CONF_TOKEN]}"
        response = await hass.async_add_executor_job(
            requests.get, url, {"timeout": 10}
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        raise CannotConnect from err

    return {"title": data[CONF_URL]}


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
                    self.hass, user_input[CONF_URL], user_input[CONF_TOKEN]
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
                _LOGGER.info(
                    "Configuration successful. URL: %s, Devices: %s",
                    user_input[CONF_URL],
                    devices,
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
        reconfigure_entry = self._async_get_entry()

        errors = {}
        if user_input is not None:
            try:
                _LOGGER.debug("Validating reconfiguration input...")
                info = await validate_input(self.hass, user_input)
                _LOGGER.debug("Reconfiguration input validated: %s", info)
                
                _LOGGER.debug("Fetching available devices for reconfiguration...")
                devices = await async_get_available_devices(
                    self.hass, user_input[CONF_URL], user_input[CONF_TOKEN]
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

        # Pre-populate with existing values
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_URL, default=reconfigure_entry.data.get(CONF_URL, "")
                ): str,
                vol.Required(
                    CONF_TOKEN, default=reconfigure_entry.data.get(CONF_TOKEN, "")
                ): str,
                vol.Optional(
                    CONF_RECONNECT_INTERVAL,
                    default=reconfigure_entry.data.get(
                        CONF_RECONNECT_INTERVAL, DEFAULT_RECONNECT_INTERVAL
                    ),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_UPDATE_TIME_MINUTES,
                    default=reconfigure_entry.data.get(
                        CONF_UPDATE_TIME_MINUTES, DEFAULT_UPDATE_TIME_MINUTES
                    ),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_UPDATE_TIME_SECONDS,
                    default=reconfigure_entry.data.get(
                        CONF_UPDATE_TIME_SECONDS, DEFAULT_UPDATE_TIME_SECONDS
                    ),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_MAX_GPS_ACCURACY,
                    default=reconfigure_entry.data.get(
                        CONF_MAX_GPS_ACCURACY, DEFAULT_MAX_GPS_ACCURACY
                    ),
                ): vol.Coerce(float),
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
