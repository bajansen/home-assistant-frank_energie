"""Frank Energie current electricity and gas price information service."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CURRENCY_EURO,
    UnitOfEnergy,
    UnitOfVolume,
)
from homeassistant.core import HassJob, HomeAssistant
from homeassistant.helpers import event
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import utcnow

from .const import (
    ATTR_TIME,
    ATTRIBUTION,
    CONF_COORDINATOR,
    DATA_ELECTRICITY,
    DATA_GAS,
    DATA_INVOICES,
    DATA_MONTH_SUMMARY,
    DOMAIN,
    ICON,
    SERVICE_NAME_PRICES,
    SERVICE_NAME_COSTS,
)
from .coordinator import FrankEnergieCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class FrankEnergieEntityDescription(SensorEntityDescription):
    """Describes Frank Energie sensor entity."""

    authenticated: bool = False
    service_name: str | None = SERVICE_NAME_PRICES
    value_fn: Callable[[dict], StateType] = None
    attr_fn: Callable[[dict], dict[str, StateType | list]] = lambda _: {}


SENSOR_TYPES: tuple[FrankEnergieEntityDescription, ...] = (
    FrankEnergieEntityDescription(
        key="elec_markup",
        name="Current electricity price (All-in)",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_ELECTRICITY].current_hour.total,
        attr_fn=lambda data: {"prices": data[DATA_ELECTRICITY].asdict("total")},
    ),
    FrankEnergieEntityDescription(
        key="elec_market",
        name="Current electricity market price",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_ELECTRICITY].current_hour.market_price,
        attr_fn=lambda data: {"prices": data[DATA_ELECTRICITY].asdict("market_price")},
    ),
    FrankEnergieEntityDescription(
        key="elec_tax",
        name="Current electricity price including tax",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_ELECTRICITY].current_hour.market_price_with_tax,
        attr_fn=lambda data: {
            "prices": data[DATA_ELECTRICITY].asdict("market_price_with_tax")
        },
    ),
    FrankEnergieEntityDescription(
        key="elec_tax_vat",
        name="Current electricity VAT price",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_ELECTRICITY].current_hour.market_price_tax,
        entity_registry_enabled_default=False,
    ),
    FrankEnergieEntityDescription(
        key="elec_sourcing",
        name="Current electricity sourcing markup",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_ELECTRICITY].current_hour.sourcing_markup_price,
        entity_registry_enabled_default=False,
    ),
    FrankEnergieEntityDescription(
        key="elec_tax_only",
        name="Current electricity tax only",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_ELECTRICITY].current_hour.energy_tax_price,
        entity_registry_enabled_default=False,
    ),
    FrankEnergieEntityDescription(
        key="gas_markup",
        name="Current gas price (All-in)",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_GAS].current_hour.total,
        attr_fn=lambda data: {"prices": data[DATA_GAS].asdict("total")},
    ),
    FrankEnergieEntityDescription(
        key="gas_market",
        name="Current gas market price",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_GAS].current_hour.market_price,
        attr_fn=lambda data: {"prices": data[DATA_GAS].asdict("market_price")},
    ),
    FrankEnergieEntityDescription(
        key="gas_tax",
        name="Current gas price including tax",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_GAS].current_hour.market_price_with_tax,
        attr_fn=lambda data: {"prices": data[DATA_GAS].asdict("market_price_with_tax")},
    ),
    FrankEnergieEntityDescription(
        key="gas_tax_vat",
        name="Current gas VAT price",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_GAS].current_hour.market_price_tax,
        entity_registry_enabled_default=False,
    ),
    FrankEnergieEntityDescription(
        key="gas_sourcing",
        name="Current gas sourcing price",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_GAS].current_hour.sourcing_markup_price,
        entity_registry_enabled_default=False,
    ),
    FrankEnergieEntityDescription(
        key="gas_tax_only",
        name="Current gas tax only",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_GAS].current_hour.energy_tax_price,
        entity_registry_enabled_default=False,
    ),
    FrankEnergieEntityDescription(
        key="gas_min",
        name="Lowest gas price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_GAS].today_min.total,
        attr_fn=lambda data: {ATTR_TIME: data[DATA_GAS].today_min.date_from},
    ),
    FrankEnergieEntityDescription(
        key="gas_max",
        name="Highest gas price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_GAS].today_max.total,
        attr_fn=lambda data: {ATTR_TIME: data[DATA_GAS].today_max.date_from},
    ),
    FrankEnergieEntityDescription(
        key="elec_min",
        name="Lowest energy price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_ELECTRICITY].today_min.total,
        attr_fn=lambda data: {ATTR_TIME: data[DATA_ELECTRICITY].today_min.date_from},
    ),
    FrankEnergieEntityDescription(
        key="elec_max",
        name="Highest energy price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_ELECTRICITY].today_max.total,
        attr_fn=lambda data: {ATTR_TIME: data[DATA_ELECTRICITY].today_max.date_from},
    ),
    FrankEnergieEntityDescription(
        key="elec_avg",
        name="Average electricity price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data[DATA_ELECTRICITY].today_avg,
    ),
    FrankEnergieEntityDescription(
        key="actual_costs_until_last_meter_reading_date",
        name="Actual monthly cost",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        authenticated=True,
        service_name=SERVICE_NAME_COSTS,
        value_fn=lambda data: data[
            DATA_MONTH_SUMMARY
        ].actualCostsUntilLastMeterReadingDate,
        attr_fn=lambda data: {
            "Last update": data[DATA_MONTH_SUMMARY].lastMeterReadingDate
        },
    ),
    FrankEnergieEntityDescription(
        key="expected_costs_until_last_meter_reading_date",
        name="Expected monthly cost until now",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        authenticated=True,
        service_name=SERVICE_NAME_COSTS,
        value_fn=lambda data: data[
            DATA_MONTH_SUMMARY
        ].expectedCostsUntilLastMeterReadingDate,
        attr_fn=lambda data: {
            "Last update": data[DATA_MONTH_SUMMARY].lastMeterReadingDate
        },
    ),
    FrankEnergieEntityDescription(
        key="expected_costs_this_month",
        name="Expected cost this month",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        authenticated=True,
        service_name=SERVICE_NAME_COSTS,
        value_fn=lambda data: data[DATA_MONTH_SUMMARY].expectedCosts,
    ),
    FrankEnergieEntityDescription(
        key="invoice_previous_period",
        name="Invoice previous period",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        authenticated=True,
        service_name=SERVICE_NAME_COSTS,
        value_fn=lambda data: data[DATA_INVOICES].previousPeriodInvoice.TotalAmount
        if data[DATA_INVOICES].previousPeriodInvoice
        else None,
        attr_fn=lambda data: {
            "Start date": data[DATA_INVOICES].previousPeriodInvoice.StartDate,
            "Description": data[DATA_INVOICES].previousPeriodInvoice.PeriodDescription,
        },
    ),
    FrankEnergieEntityDescription(
        key="invoice_current_period",
        name="Invoice current period",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        authenticated=True,
        service_name=SERVICE_NAME_COSTS,
        value_fn=lambda data: data[DATA_INVOICES].currentPeriodInvoice.TotalAmount
        if data[DATA_INVOICES].currentPeriodInvoice
        else None,
        attr_fn=lambda data: {
            "Start date": data[DATA_INVOICES].currentPeriodInvoice.StartDate,
            "Description": data[DATA_INVOICES].currentPeriodInvoice.PeriodDescription,
        },
    ),
    FrankEnergieEntityDescription(
        key="invoice_upcoming_period",
        name="Invoice upcoming period",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        authenticated=True,
        service_name=SERVICE_NAME_COSTS,
        value_fn=lambda data: data[DATA_INVOICES].upcomingPeriodInvoice.TotalAmount
        if data[DATA_INVOICES].upcomingPeriodInvoice
        else None,
        attr_fn=lambda data: {
            "Start date": data[DATA_INVOICES].upcomingPeriodInvoice.StartDate,
            "Description": data[DATA_INVOICES].upcomingPeriodInvoice.PeriodDescription,
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Frank Energie sensor entries."""
    frank_coordinator = hass.data[DOMAIN][config_entry.entry_id][CONF_COORDINATOR]

    # Add an entity for each sensor type, when authenticated is True,
    # only add the entity if the user is authenticated
    async_add_entities(
        [
            FrankEnergieSensor(frank_coordinator, description, config_entry)
            for description in SENSOR_TYPES
            if not description.authenticated or frank_coordinator.api.is_authenticated
        ],
        True,
    )


class FrankEnergieSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Frank Energie sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_icon = ICON

    def __init__(
        self,
        coordinator: FrankEnergieCoordinator,
        description: FrankEnergieEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description: FrankEnergieEntityDescription = description
        self._attr_unique_id = f"{entry.unique_id}.{description.key}"

        # Do not set extra identifier for default service, backwards compatibility
        if description.service_name is SERVICE_NAME_PRICES:
            device_info_identifiers = {(DOMAIN, f"{entry.entry_id}")}
        else:
            device_info_identifiers = {(DOMAIN, f"{entry.entry_id}", description.service_name)}

        self._attr_device_info = DeviceInfo(
            identifiers=device_info_identifiers,
            name=f"Frank Energie - {description.service_name}",
            manufacturer="Frank Energie",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.frankenergie.nl/goedkoop",
        )

        self._update_job = HassJob(self._handle_scheduled_update)
        self._unsub_update = None

        super().__init__(coordinator)

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""
        try:
            self._attr_native_value = self.entity_description.value_fn(
                self.coordinator.data
            )
        except (TypeError, IndexError, ValueError):
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

    async def _handle_scheduled_update(self, _):
        """Handle a scheduled update."""
        # Only handle the scheduled update for entities which have a reference to hass,
        # which disabled sensors don't have.
        if self.hass is None:
            return

        self.async_schedule_update_ha_state(True)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self.entity_description.attr_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None
