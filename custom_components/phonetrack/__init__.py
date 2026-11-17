"""The phonetrack component."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS = [Platform.DEVICE_TRACKER]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PhoneTrack from a config entry."""
    _LOGGER.debug("Setting up PhoneTrack entry: %s", entry.entry_id)
    _LOGGER.debug("Entry data: %s", entry.data)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Set up the device tracker platform
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _LOGGER.info("PhoneTrack integration setup completed successfully")
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.exception(
            "Failed to set up PhoneTrack platform: %s", err
        )
        raise

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading PhoneTrack entry: %s", entry.entry_id)
    try:
        if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
            hass.data[DOMAIN].pop(entry.entry_id)
            _LOGGER.info("PhoneTrack entry unloaded successfully")
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.exception("Error unloading PhoneTrack entry: %s", err)
        return False

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    _LOGGER.debug("Updating PhoneTrack options for entry: %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry."""
    _LOGGER.debug(
        "Migrating from entry version %s.%s", entry.version, entry.minor_version
    )

    if entry.version > 1:
        # We don't support older versions than 1
        _LOGGER.error("Unsupported entry version: %s", entry.version)
        return False

    if entry.version == 1 and entry.minor_version < 1:
        # Migrate from legacy format to new format
        _LOGGER.debug("Migrating from version 1.0 to 1.1")
        new_data = {**entry.data}

        # Add default reconnect interval if not present
        from .const import CONF_DEVICES, CONF_RECONNECT_INTERVAL, DEFAULT_RECONNECT_INTERVAL

        if CONF_RECONNECT_INTERVAL not in new_data:
            new_data[CONF_RECONNECT_INTERVAL] = DEFAULT_RECONNECT_INTERVAL
            _LOGGER.debug("Added default reconnect interval")

        # Convert devices from string to list if needed (for legacy format)
        devices = new_data.get(CONF_DEVICES, [])
        if isinstance(devices, str):
            # Split the string by comma and strip whitespace
            new_data[CONF_DEVICES] = [d.strip() for d in devices.split(",") if d.strip()]
            _LOGGER.debug("Converted devices string to list: %s", new_data[CONF_DEVICES])

        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            version=1,
            minor_version=1,
        )

        _LOGGER.info("Migration to version 1.1 complete")

    return True
