from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.util import dt
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    MockConfigEntry,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.frank_energie import const, sensor
from tests.utils import ResponseMocks


@pytest.fixture
async def frank_energie_config_entry(hass: HomeAssistant, enable_custom_integrations):
    config_entry = MockConfigEntry(
        domain=const.DOMAIN,
        data={},
        unique_id=const.UNIQUE_ID,
    )
    config_entry.add_to_hass(hass)

    return config_entry


@pytest.fixture
def aioclient_responses(aioclient_mock: AiohttpClientMocker, socket_enabled):
    responses = ResponseMocks()

    async def next_response(*_):
        return next(responses)

    aioclient_mock.post(const.DATA_URL, side_effect=next_response)

    return responses


def price_generator(base: float, var: float) -> list:
    """
    Return a list of 24 prices which has two peaks of price `base` and 3 bottoms of `base - 6 * var`.
    :param base:
    :param var:
    :return:
    """
    return [round(base - var * abs(6 - (i % 12)), 3) for i in range(24)]


async def enable_all_sensors(hass):
    """Enable all sensors of the integration."""
    er = entity_registry.async_get(hass)
    for sensor_type in sensor.SENSOR_TYPES:
        if sensor_type.entity_registry_enabled_default is False:
            entity_id = generate_entity_id("sensor.{}", sensor_type.name, hass=hass)
            er.async_update_entity(entity_id, disabled_by=None)
    await hass.async_block_till_done()
    await trigger_update(hass)


async def trigger_update(hass, delta_seconds=config_entries.RELOAD_AFTER_UPDATE_DELAY):
    """Trigger a reload of the data"""
    async_fire_time_changed(
        hass,
        dt.utcnow() + timedelta(seconds=delta_seconds + 1),
    )
    await hass.async_block_till_done()


@patch("frank_energie.price_data.dt.now")
async def test_sensors(
    dt_mock,
    aioclient_responses: ResponseMocks,
    frank_energie_config_entry: MockConfigEntry,
    hass: HomeAssistant,
):
    hass.config.set_time_zone("Europe/Amsterdam")
    dt_mock.return_value = (
        datetime.utcnow()
        .replace(hour=14, minute=15, second=0, microsecond=0)
        .astimezone()
    )
    start_of_day = datetime.utcnow().replace(hour=0, minute=0)
    aioclient_responses.add(
        start_of_day,
        [0.2] * 10 + [0.25, 0.3, 0.5, 0.4] + [0.15] * 10,
        [1.75] * 6 + [1.23] * 18,
    )
    aioclient_responses.add(
        start_of_day + timedelta(days=1),
        [0.3] * 12 + [0.15] * 12,
        [1.23] * 24,
    )
    aioclient_responses.cyclic()

    await hass.config_entries.async_setup(frank_energie_config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the state of all sensors which are enabled by default
    assert hass.states.get("sensor.current_electricity_price_all_in").state == "0.15"
    assert hass.states.get("sensor.current_electricity_market_price").state == "0.105"
    assert (
        hass.states.get("sensor.current_electricity_price_including_tax").state
        == "0.1125"
    )
    assert hass.states.get("sensor.current_gas_price_all_in").state == "1.23"
    assert hass.states.get("sensor.current_gas_market_price").state == "0.861"
    assert hass.states.get("sensor.current_gas_price_including_tax").state == "0.9225"
    assert hass.states.get("sensor.lowest_gas_price_today").state == "1.23"
    assert hass.states.get("sensor.highest_gas_price_today").state == "1.75"
    assert hass.states.get("sensor.lowest_energy_price_today").state == "0.15"
    assert hass.states.get("sensor.highest_energy_price_today").state == "0.5"
    assert hass.states.get("sensor.average_electricity_price_today").state == "0.20625"

    # Check that the disabled sensors are None
    assert hass.states.get("sensor.current_electricity_vat_price") is None
    assert hass.states.get("sensor.current_electricity_sourcing_markup") is None
    assert hass.states.get("sensor.current_electricity_tax_only") is None
    assert hass.states.get("sensor.current_gas_vat_price") is None
    assert hass.states.get("sensor.current_gas_sourcing_price") is None
    assert hass.states.get("sensor.current_gas_tax_only") is None

    # Enable all sensor and check their expected values
    await enable_all_sensors(hass)
    assert hass.states.get("sensor.current_electricity_vat_price").state == "0.0075"
    assert (
        hass.states.get("sensor.current_electricity_sourcing_markup").state == "0.015"
    )
    assert hass.states.get("sensor.current_electricity_tax_only").state == "0.0225"
    assert hass.states.get("sensor.current_gas_vat_price").state == "0.0615"
    assert hass.states.get("sensor.current_gas_sourcing_price").state == "0.123"
    assert hass.states.get("sensor.current_gas_tax_only").state == "0.1845"


@patch("frank_energie.price_data.dt.now")
async def test_sensors_get_data_of_current_hour(
    dt_mock,
    aioclient_responses: ResponseMocks,
    frank_energie_config_entry: MockConfigEntry,
    hass: HomeAssistant,
):
    hass.config.set_time_zone("Europe/Amsterdam")
    dt_mock.return_value = (
        datetime.utcnow()
        .replace(hour=5, minute=15, second=0, microsecond=0)
        .astimezone()
    )
    start_of_day = datetime.utcnow().replace(hour=0, minute=0)
    aioclient_responses.add(
        start_of_day, [0.3] * 12 + [0.15] * 12, [1.75] * 6 + [1.23] * 18
    )
    aioclient_responses.add(
        start_of_day + timedelta(days=1),
        [0.25] * 12 + [0.1] * 12,
        [1.23] * 6 + [1.11] * 18,
    )
    aioclient_responses.cyclic()

    await hass.config_entries.async_setup(frank_energie_config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the state at 5:15
    assert hass.states.get("sensor.current_electricity_price_all_in").state == "0.3"
    assert hass.states.get("sensor.current_gas_price_all_in").state == "1.75"

    # Change time to 12:15
    dt_mock.return_value = (
        datetime.utcnow()
        .replace(hour=12, minute=15, second=0, microsecond=0)
        .astimezone()
    )
    await trigger_update(hass, 7 * 3600)

    assert hass.states.get("sensor.current_electricity_price_all_in").state == "0.15"
    assert hass.states.get("sensor.current_gas_price_all_in").state == "1.23"


@patch("frank_energie.price_data.dt.now")
async def test_sensors_no_data_for_tomorrow(
    dt_mock,
    aioclient_responses: ResponseMocks,
    frank_energie_config_entry: MockConfigEntry,
    hass: HomeAssistant,
):
    hass.config.set_time_zone("Europe/Amsterdam")
    dt_mock.return_value = (
        datetime.utcnow()
        .replace(hour=20, minute=0, second=0, microsecond=0)
        .astimezone()
    )
    start_of_day = datetime.utcnow().replace(hour=0, minute=0)

    # First response is for today's data, 2nd for tomorrow's data
    aioclient_responses.add(start_of_day, [0.3] * 24, [1.75] * 6 + [1.23] * 18)
    aioclient_responses.add(start_of_day + timedelta(days=1), [], [])

    await hass.config_entries.async_setup(frank_energie_config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the state at 5:15
    assert hass.states.get("sensor.current_electricity_price_all_in").state == "0.3"
    assert hass.states.get("sensor.current_gas_price_all_in").state == "1.23"


@patch("frank_energie.price_data.dt.now")
async def test_sensors_hour_price_attr(
    dt_mock,
    aioclient_responses: ResponseMocks,
    frank_energie_config_entry: MockConfigEntry,
    hass: HomeAssistant,
):
    hass.config.set_time_zone("Europe/Amsterdam")
    dt_mock.return_value = (
        datetime.utcnow()
        .replace(hour=20, minute=0, second=0, microsecond=0)
        .astimezone()
    )
    start_of_day = datetime.utcnow().replace(hour=0, minute=0)

    # First response is for today's data, 2nd for tomorrow's data
    aioclient_responses.add(
        start_of_day, price_generator(0.25, 0.05), gas_prices=[1.75] * 6 + [1.23] * 18
    )
    aioclient_responses.add(
        start_of_day + timedelta(days=1),
        price_generator(0.3, 0.02),
        gas_prices=[1.23] * 6 + [0.75] * 18,
    )

    await hass.config_entries.async_setup(frank_energie_config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the all in electricity prices
    price_attr = [
        a["price"]
        for a in hass.states.get("sensor.current_electricity_price_all_in").attributes[
            "prices"
        ]
    ]
    assert price_attr == price_generator(0.25, 0.05) + price_generator(0.3, 0.02)

    # Check the all in electricity prices
    price_attr = [
        a["price"]
        for a in hass.states.get("sensor.current_gas_price_all_in").attributes["prices"]
    ]
    assert price_attr == [1.75] * 6 + [1.23] * 24 + [0.75] * 18

    # For the other sensors just check if the prices attribute is there
    assert 48 == len(
        hass.states.get("sensor.current_electricity_market_price").attributes["prices"]
    )
    assert 48 == len(
        hass.states.get("sensor.current_electricity_price_including_tax").attributes[
            "prices"
        ]
    )
    assert 48 == len(
        hass.states.get("sensor.current_gas_market_price").attributes["prices"]
    )
    assert 48 == len(
        hass.states.get("sensor.current_gas_price_including_tax").attributes["prices"]
    )
