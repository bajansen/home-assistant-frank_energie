"""Frank Energie current electricity and gas price information service."""
from __future__ import annotations

import asyncio
from typing import List, Tuple
import aiohttp
from datetime import datetime, date, timedelta
import logging

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
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

ATTRIBUTION = "Data provided by Frank Energie"

DOMAIN="frank_energie"

DATA_URL = "https://frank-graphql-prod.graphcdn.app/"

ICON = "mdi:currency-eur"

SCAN_INTERVAL = timedelta(minutes=1)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="elec_markup",
        name="Current electricity price (All-in)",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
    ),
    SensorEntityDescription(
        key="elec_market",
        name="Current electricity market price",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
    ),
    SensorEntityDescription(
        key="elec_tax",
        name="Current electricity price including tax",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
    ),
    SensorEntityDescription(
        key="gas_markup",
        name="Current gas price (All-in)",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
    ),
    SensorEntityDescription(
        key="gas_market",
        name="Current gas market price",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
    ),
    SensorEntityDescription(
        key="gas_tax",
        name="Current gas price including tax",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
    ),
    SensorEntityDescription(
        key="gas_min",
        name="Lowest gas price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
    ),
    SensorEntityDescription(
        key="gas_max",
        name="Highest gas price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
    ),
    SensorEntityDescription(
        key="elec_min",
        name="Lowest energy price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
    ),
    SensorEntityDescription(
        key="elec_max",
        name="Highest energy price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
    ),
    SensorEntityDescription(
        key="elec_avg",
        name="Average electricity price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
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

    data = FrankEnergieData(websession)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name="sensor",
        update_method=data.async_fetch_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(minutes=15),
    )

    entities = [
        FrankEnergieSensor(coordinator, data, description)
        for description in SENSOR_TYPES
        if description.key in config[CONF_DISPLAY_OPTIONS]
    ]

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(entities, True)

class FrankEnergieSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Frank Energie sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_icon = ICON

    def __init__(self, coordinator, data, description: SensorEntityDescription) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self.data = data
        super().__init__(coordinator)

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""

        if self.data._elec_data and self.data._gas_data:
            _LOGGER.debug("updating sensors")

            elec = self.get_current_hourprices(self.data._elec_data)
            gas = self.get_current_hourprices(self.data._gas_data)
            today_gas = self.get_hourprices(self.data._gas_data)
            today_elec = self.get_hourprices(self.data._elec_data)

            sensor_type = self.entity_description.key
            if sensor_type == "elec_markup":
                self._attr_native_value = elec[1]
            elif sensor_type == "elec_market":
                self._attr_native_value = elec[0]
            elif sensor_type == "elec_tax":
                self._attr_native_value = elec[0] + elec[2]
            elif sensor_type == "gas_markup":
                self._attr_native_value = gas[1]
            elif sensor_type == "gas_market":
                self._attr_native_value = gas[0]
            elif sensor_type == "gas_tax":
                self._attr_native_value = gas[0] + gas[2]
            elif sensor_type == "gas_max":
                self._attr_native_value = max(today_gas)
            elif sensor_type == "gas_min":
                self._attr_native_value = min(today_gas)
            elif sensor_type == "elec_max":
                self._attr_native_value = max(today_elec)
            elif sensor_type == "elec_min":
                self._attr_native_value = min(today_elec)
            elif sensor_type == "elec_avg":
                self._attr_native_value = round(sum(today_elec) / len(today_elec), 5)

    def get_current_hourprices(self, hourprices) -> Tuple:
        # hack to compare to datestring in json data
        current_hour = str(datetime.utcnow().replace(microsecond=0,second=0,minute=0).isoformat()) + '.000Z'

        for hour in hourprices:
            if hour['from'] == current_hour:
                return hour['marketPrice'], hour['priceIncludingMarkup'], hour['marketPriceTax']

    def get_hourprices(self, hourprices) -> List:
        today_prices = []
        for hour in hourprices:
            today_prices.append(hour['priceIncludingMarkup'])
        return today_prices

class FrankEnergieData:
    """Get the latest data and update the states."""

    def __init__(self, websession) -> None:
        """Initialize the data object."""
        self.websession = websession
        self._elec_data = None
        self._gas_data = None
        self._last_update = None

    async def async_fetch_data(self) -> None:
        """Get the latest data from Frank Energie"""
        _LOGGER.debug("Fetching Frank Energie data")
        # We request data for today up until the day after tomorrow. This is to ensure we always request all available data.
        today = date.today()
        tomorrow = today + timedelta(days = 2)
        query_data = {	"query": "query MarketPrices($startDate: Date!, $endDate: Date!) { marketPricesElectricity(startDate: $startDate, endDate: $endDate) { from till marketPrice marketPriceTax priceIncludingMarkup } marketPricesGas(startDate: $startDate, endDate: $endDate) { from till marketPrice marketPriceTax priceIncludingMarkup } }",
            "variables": { "startDate":str(today),"endDate":str(tomorrow) },
            "operationName": "MarketPrices"
        }
        try:
            resp = await self.websession.post(DATA_URL, json=query_data)
        except (asyncio.TimeoutError, aiohttp.ClientError):
            return

        data = await resp.json()
        self._elec_data = data['data']['marketPricesElectricity']
        self._gas_data = data['data']['marketPricesGas']
        self._last_update = datetime.now()
