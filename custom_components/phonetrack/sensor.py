"""Support for PhoneTrack sensor entities."""
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .device_tracker import PhoneTrackDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Sensor entity description for battery level
SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key="batterylevel",
        name="Battery Level",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement="%",
        icon="mdi:battery",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up PhoneTrack sensor from a config entry."""
    _LOGGER.debug("Setting up PhoneTrack sensors")

    # Get configuration from config entry
    config = entry.data
    devices = config.get("devices", [])

    _LOGGER.debug("Configured devices: %s", devices)

    if not devices:
        _LOGGER.warning("No devices configured, no sensor entities will be created")
        return

    # Create coordinator for managing updates
    coordinator = PhoneTrackDataUpdateCoordinator(hass, config)

    # Create sensor entity for each device
    entities = []
    for device in devices:
        _LOGGER.debug("Creating sensor entity for device: %s", device)
        for description in SENSOR_DESCRIPTIONS:
            entities.append(
                PhoneTrackSensor(
                    coordinator,
                    device,
                    description,
                    entry.entry_id,
                )
            )

    _LOGGER.info("Adding %d sensor entities", len(entities))
    async_add_entities(entities, True)


class PhoneTrackSensor(CoordinatorEntity, SensorEntity):
    """A sensor entity using PhoneTrack data (battery level)."""

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = True

    def __init__(
        self,
        coordinator: PhoneTrackDataUpdateCoordinator,
        device: str,
        description: SensorEntityDescription,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.device = device
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{device}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_{device}")},
            "name": device,
            "manufacturer": "PhoneTrack",
        }
        _LOGGER.debug(
            "Initialized PhoneTrackSensor for %s with unique_id: %s",
            device,
            self._attr_unique_id,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> int | None:
        """Return the value of the sensor."""
        if self.coordinator.data is None:
            return None
        if self.device not in self.coordinator.data:
            return None
        return self.coordinator.data[self.device].get(self.entity_description.key)

    @callback
    def _async_update_attrs(self) -> None:
        """Update attributes from coordinator data."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._async_update_attrs()
