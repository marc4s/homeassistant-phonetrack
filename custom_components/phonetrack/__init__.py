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
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Set up the device tracker platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry."""
    _LOGGER.debug("Migrating from entry version %s.%s", entry.version, entry.minor_version)

    if entry.version > 1:
        # We don't support older versions than 1
        return False

    if entry.version == 1 and entry.minor_version < 1:
        # Migrate from legacy format to new format
        _LOGGER.debug("Migrating from version 1.0 to 1.1")
        new_data = {**entry.data}

        # Add default reconnect interval if not present
        from .const import CONF_RECONNECT_INTERVAL, DEFAULT_RECONNECT_INTERVAL

        if CONF_RECONNECT_INTERVAL not in new_data:
            new_data[CONF_RECONNECT_INTERVAL] = DEFAULT_RECONNECT_INTERVAL

        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            version=1,
            minor_version=1,
        )

        _LOGGER.debug("Migration to version 1.1 complete")

    return True
