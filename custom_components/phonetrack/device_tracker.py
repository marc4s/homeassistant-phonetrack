"""Support for PhoneTrack device tracking using modern API."""
import logging
import urllib.parse
from datetime import timedelta
from typing import Any

import requests
from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_DEVICES,
    CONF_MAX_GPS_ACCURACY,
    CONF_RECONNECT_INTERVAL,
    CONF_TOKEN,
    CONF_URL,
    CONF_UPDATE_TIME_MINUTES,
    CONF_UPDATE_TIME_SECONDS,
    CONF_VERIFY_SSL,
    DEFAULT_MAX_GPS_ACCURACY,
    DEFAULT_RECONNECT_INTERVAL,
    DEFAULT_UPDATE_TIME_MINUTES,
    DEFAULT_UPDATE_TIME_SECONDS,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Mapping from old config keys to new config entry data keys
CONFIG_KEYS = [
    CONF_DEVICES,
    CONF_TOKEN,
    CONF_URL,
    CONF_MAX_GPS_ACCURACY,
    CONF_UPDATE_TIME_MINUTES,
    CONF_UPDATE_TIME_SECONDS,
    CONF_RECONNECT_INTERVAL,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up PhoneTrack device tracker from a config entry."""
    _LOGGER.debug("Setting up PhoneTrack device tracker")
    _LOGGER.debug("Entry data: %s", entry.data)

    # Get configuration from config entry
    config = entry.data
    devices = config.get(CONF_DEVICES, [])

    _LOGGER.debug("Configured devices: %s", devices)

    # Validate devices list
    if not devices:
        _LOGGER.warning("No devices configured, no entities will be created")
        return

    if not isinstance(devices, list):
        _LOGGER.error("Devices must be a list, got %s", type(devices))
        return

    # Create coordinator for managing updates
    _LOGGER.debug("Creating DataUpdateCoordinator")
    coordinator = PhoneTrackDataUpdateCoordinator(hass, config)

    # Create entity for each device
    entities = []
    for device in devices:
        _LOGGER.debug("Creating entity for device: %s", device)
        entities.append(PhoneTrackDevice(coordinator, device, entry.entry_id))

    _LOGGER.info("Adding %d device tracker entities", len(entities))
    async_add_entities(entities, True)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry to new format."""
    _LOGGER.debug("Migrating from entry version %s", entry.version)

    if entry.version == 1:
        # Migrate from legacy platform format to config entry
        # This handles migration from the old setup_scanner approach
        new_data = {**entry.data}

        # Add default reconnect interval if not present
        if CONF_RECONNECT_INTERVAL not in new_data:
            new_data[CONF_RECONNECT_INTERVAL] = DEFAULT_RECONNECT_INTERVAL

        # Update the config entry
        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            version=entry.version,
            minor_version=entry.minor_version + 1,
        )

        _LOGGER.debug("Migration to entry version %s successful", entry.version)

    return True


class PhoneTrackDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching PhoneTrack data from the server."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=config.get(CONF_UPDATE_TIME_MINUTES, DEFAULT_UPDATE_TIME_MINUTES),
                seconds=config.get(CONF_UPDATE_TIME_SECONDS, DEFAULT_UPDATE_TIME_SECONDS),
            ),
        )
        self.config = config
        self.url = config[CONF_URL]
        self.token = config[CONF_TOKEN]
        self.devices = config.get(CONF_DEVICES, [])
        self.max_gps_accuracy = config.get(
            CONF_MAX_GPS_ACCURACY, DEFAULT_MAX_GPS_ACCURACY
        )
        self.reconnect_interval = config.get(
            CONF_RECONNECT_INTERVAL, DEFAULT_RECONNECT_INTERVAL
        )
        self.verify_ssl = config.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        _LOGGER.debug("verify_ssl set to: %s", self.verify_ssl)
        self._connected = True  # Start assuming connected
        _LOGGER.debug(
            "Coordinator initialized with URL: %s, devices: %s, verify_ssl: %s",
            self.url,
            self.devices,
            self.verify_ssl,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data from the PhoneTrack server."""
        _LOGGER.debug("Updating data from PhoneTrack server")
        import asyncio

        # Use asyncio.to_thread for sync requests
        def fetch_data():
            # Ensure the URL ends with /getlastpositions/ before appending token
            url = self.url
            if not url.endswith("/getlastpositions") and not url.endswith("/getlastpositions/"):
                url = url.rstrip("/") + "/getlastpositions"
            
            # Build the full URL by appending the token
            url_full = url.rstrip("/") + "/" + self.token
            _LOGGER.debug("Fetching data from: %s", url_full)
            response = requests.get(url_full, timeout=30, verify=self.verify_ssl)
            response.raise_for_status()
            return response.json()

        try:
            data = await asyncio.to_thread(fetch_data)

            # Check if the response contains the expected token data
            if self.token not in data:
                _LOGGER.error(
                    "Server response does not contain expected token data: %s", self.token
                )
                raise UpdateFailed(f"Missing token data in server response")

            _LOGGER.debug("Successfully updated data for %d devices", len(data[self.token]))
            return data[self.token]

        except requests.exceptions.RequestException as err:
            # Handle connection errors
            if self._connected:
                _LOGGER.warning(
                    "Cannot connect to PhoneTrack server (will retry in %ds): %s",
                    self.reconnect_interval,
                    err,
                )
                self._connected = False
            else:
                _LOGGER.debug(
                    "Still disconnected from PhoneTrack server (retry in %ds): %s",
                    self.reconnect_interval,
                    err,
                )

            raise UpdateFailed(f"Error fetching PhoneTrack data: {err}") from err


class PhoneTrackDevice(CoordinatorEntity, TrackerEntity):
    """A device tracker using PhoneTrack data."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_tracker_source_type = "gps"
    _attr_tracking_type = "position"

    def __init__(
        self, coordinator: PhoneTrackDataUpdateCoordinator, device: str, entry_id: str
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self.device = device
        self._attr_unique_id = f"{entry_id}_{device}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": device,
            "manufacturer": "PhoneTrack",
        }
        _LOGGER.debug(
            "Initialized PhoneTrackDevice for %s with unique_id: %s",
            device,
            self._attr_unique_id,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def in_zones(self) -> list[str] | None:
        """Return the zones the device is currently in."""
        # PhoneTrack doesn't provide zone information directly
        # We'll let Home Assistant determine zones based on coordinates
        return None

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        if self.coordinator.data is None:
            return None
        if self.device not in self.coordinator.data:
            return None
        lat = self.coordinator.data[self.device].get("lat")
        return float(lat) if lat is not None else None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        if self.coordinator.data is None:
            return None
        if self.device not in self.coordinator.data:
            return None
        lon = self.coordinator.data[self.device].get("lon")
        return float(lon) if lon is not None else None

    @property
    def location_accuracy(self) -> float:
        """Return the gps accuracy of the device."""
        if self.coordinator.data is None:
            return 0
        if self.device not in self.coordinator.data:
            return 0
        return self.coordinator.data[self.device].get("accuracy", 0)

    @callback
    def _async_update_attrs(self) -> None:
        """Update attributes from coordinator data."""
        if self.coordinator.data is None:
            _LOGGER.debug("Coordinator data is None, skipping update for %s", self.device)
            return
        if self.device not in self.coordinator.data:
            _LOGGER.debug(
                "Device %s not in coordinator data, skipping update", self.device
            )
            return

        device_data = self.coordinator.data[self.device]

        # Check GPS accuracy if configured
        max_accuracy = self.coordinator.max_gps_accuracy
        if (
            max_accuracy is not None
            and device_data.get("accuracy", 0) > max_accuracy
        ):
            _LOGGER.info(
                "Skipping update for %s because GPS accuracy (%s) is not met (max: %s)",
                self.device,
                device_data.get("accuracy"),
                max_accuracy,
            )
            return

        _LOGGER.debug("Updated attributes for %s", self.device)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._async_update_attrs()

    async def async_update(self) -> None:
        """Update the entity."""
        await self.coordinator.async_request_refresh()
