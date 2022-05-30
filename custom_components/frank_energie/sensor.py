"""Frank Energie current electricity and gas price information service."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, timedelta
import logging
from typing import Callable, List, Tuple

import aiohttp
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    CONF_DISPLAY_OPTIONS,
    CURRENCY_EURO,
    ENERGY_KILO_WATT_HOUR,
    VOLUME_CUBIC_METERS,
)
from homeassistant.core import HassJob, HomeAssistant
from homeassistant.helpers import event
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt, utcnow

ATTRIBUTION = "Data provided by Frank Energie"
DOMAIN = "frank_energie"
DATA_URL = "https://frank-graphql-prod.graphcdn.app/"
ICON = "mdi:currency-eur"


@dataclass
class FrankEnergieEntityDescription(SensorEntityDescription):
    """Describes Frank Energie sensor entity."""
    value_fn: Callable[[dict], StateType] = None


SENSOR_TYPES: tuple[FrankEnergieEntityDescription, ...] = (
    FrankEnergieEntityDescription(
        key="elec_markup",
        name="Current electricity price (All-in)",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        value_fn=lambda data: sum(data['elec']),
    ),
    FrankEnergieEntityDescription(
        key="elec_market",
        name="Current electricity market price",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        value_fn=lambda data: data['elec'][0],
    ),
    FrankEnergieEntityDescription(
        key="elec_tax",
        name="Current electricity price including tax",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        value_fn=lambda data: data['elec'][0] + data['elec'][1],
    ),
    FrankEnergieEntityDescription(
        key="gas_markup",
        name="Current gas price (All-in)",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
        value_fn=lambda data: sum(data['gas']),
    ),
    FrankEnergieEntityDescription(
        key="gas_market",
        name="Current gas market price",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
        value_fn=lambda data: data['gas'][0],
    ),
    FrankEnergieEntityDescription(
        key="gas_tax",
        name="Current gas price including tax",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
        value_fn=lambda data: data['gas'][0] + data['gas'][1],
    ),
    FrankEnergieEntityDescription(
        key="gas_min",
        name="Lowest gas price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
        value_fn=lambda data: min(data['today_gas']),
    ),
    FrankEnergieEntityDescription(
        key="gas_max",
        name="Highest gas price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
        value_fn=lambda data: max(data['today_gas']),
    ),
    FrankEnergieEntityDescription(
        key="elec_min",
        name="Lowest energy price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        value_fn=lambda data: min(data['today_elec']),
    ),
    FrankEnergieEntityDescription(
        key="elec_max",
        name="Highest energy price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        value_fn=lambda data: max(data['today_elec']),
    ),
    FrankEnergieEntityDescription(
        key="elec_avg",
        name="Average electricity price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        value_fn=lambda data: round(sum(data['today_elec']) / len(data['today_elec']), 5)
    ),
)

_LOGGER = logging.getLogger(__name__)

OPTION_KEYS = [desc.key for desc in SENSOR_TYPES]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DISPLAY_OPTIONS, default=[]): vol.All(
            cv.ensure_list, [vol.In(OPTION_KEYS)]
        ),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None) -> None:
    """Set up the Frank Energie sensors."""
    _LOGGER.debug("Setting up Frank")

    websession = async_get_clientsession(hass)

    coordinator = FrankEnergieCoordinator(hass, websession)

    entities = [
        FrankEnergieSensor(coordinator, description)
        for description in SENSOR_TYPES
        if description.key in config[CONF_DISPLAY_OPTIONS]
    ]

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(entities, True)


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
        self._attr_native_value = self.entity_description.value_fn(self.coordinator.processed_data())

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


class FrankEnergieCoordinator(DataUpdateCoordinator):
    """Get the latest data and update the states."""

    def __init__(self, hass: HomeAssistant, websession) -> None:
        """Initialize the data object."""
        self.hass = hass
        self.websession = websession

        logger = logging.getLogger(__name__)
        super().__init__(
            hass,
            logger,
            name="Frank Energie coordinator",
            update_interval=timedelta(minutes=15),
        )

    async def _async_update_data(self) -> dict:
        """Get the latest data from Frank Energie"""
        self.logger.debug("Fetching Frank Energie data")

        # We request data for today up until the day after tomorrow.
        # This is to ensure we always request all available data.
        today = date.today()
        tomorrow = today + timedelta(days=2)
        query_data = {
            "query": """
                query MarketPrices($startDate: Date!, $endDate: Date!) {
                     marketPricesElectricity(startDate: $startDate, endDate: $endDate) { 
                        from till marketPrice marketPriceTax sourcingMarkupPrice energyTaxPrice 
                     } 
                     marketPricesGas(startDate: $startDate, endDate: $endDate) { 
                        from till marketPrice marketPriceTax sourcingMarkupPrice energyTaxPrice 
                     } 
                }
            """,
            "variables": {"startDate": str(today), "endDate": str(tomorrow)},
            "operationName": "MarketPrices"
        }
        try:
            resp = await self.websession.post(DATA_URL, json=query_data)

            data = await resp.json()
            return data['data']

        except (asyncio.TimeoutError, aiohttp.ClientError, KeyError) as error:
            raise UpdateFailed(f"Fetching energy data failed: {error}") from error

    def processed_data(self):
        return {
            'elec': self.get_current_hourprices(self.data['marketPricesElectricity']),
            'gas': self.get_current_hourprices(self.data['marketPricesGas']),
            'today_elec': self.get_hourprices(self.data['marketPricesElectricity']),
            'today_gas': self.get_hourprices(self.data['marketPricesGas'])
        }

    def get_current_hourprices(self, hourprices) -> Tuple:
        for hour in hourprices:
            if dt.parse_datetime(hour['from']) <= dt.utcnow() < dt.parse_datetime(hour['till']):
                return hour['marketPrice'], hour['marketPriceTax'], hour['sourcingMarkupPrice'], hour['energyTaxPrice']

    def get_hourprices(self, hourprices) -> List:
        today_prices = []
        for hour in hourprices:
            today_prices.append(
                (hour['marketPrice'] + hour['marketPriceTax'] + hour['sourcingMarkupPrice'] + hour['energyTaxPrice'])
            )
        return today_prices
