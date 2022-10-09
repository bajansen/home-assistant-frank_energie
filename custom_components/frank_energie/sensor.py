"""Frank Energie current electricity and gas price information service."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HassJob, HomeAssistant
from homeassistant.helpers import event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import utcnow
from .const import ATTRIBUTION, CONF_COORDINATOR, DOMAIN, FrankEnergieEntityDescription, ICON, SENSOR_TYPES
from .coordinator import FrankEnergieCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Frank Energie sensor entries."""
    frank_coordinator = hass.data[DOMAIN][config_entry.entry_id][CONF_COORDINATOR]

    # Add an entity for each sensor type
    async_add_entities([
        FrankEnergieSensor(frank_coordinator, description)
        for description in SENSOR_TYPES
    ], True)


class FrankEnergieSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Frank Energie sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_icon = ICON

    def __init__(self, coordinator: FrankEnergieCoordinator, description: FrankEnergieEntityDescription) -> None:
        """Initialize the sensor."""
        self.entity_description: FrankEnergieEntityDescription = description
        self._attr_unique_id = f"frank_energie.{description.key}"

        self._update_job = HassJob(self.async_schedule_update_ha_state)
        self._unsub_update = None

        super().__init__(coordinator)

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""
        try:
            self._attr_native_value = self.entity_description.value_fn(self.coordinator.processed_data())
        except (TypeError, IndexError):
            # No data available
            self._attr_native_value = None

        # Cancel the currently scheduled event if there is any
        if self._unsub_update:
            self._unsub_update()
            self._unsub_update = None

        # Schedule the next update at exactly the next whole hour sharp
        self._unsub_update = event.async_track_point_in_utc_time(
            self.hass,
            self._update_job,
            utcnow().replace(minute=0, second=0) + timedelta(hours=1),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self.entity_description.attr_fn(self.coordinator.processed_data())
