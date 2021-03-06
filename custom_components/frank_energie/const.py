from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorEntityDescription,
)
from homeassistant.const import (
    CURRENCY_EURO,
    ENERGY_KILO_WATT_HOUR,
    VOLUME_CUBIC_METERS,
)
from homeassistant.helpers.typing import StateType

ATTRIBUTION = "Data provided by Frank Energie"
DOMAIN = "frank_energie"
DATA_URL = "https://frank-graphql-prod.graphcdn.app/"
ICON = "mdi:currency-eur"
UNIQUE_ID = f"{DOMAIN}_component"
COMPONENT_TITLE = "Frank Energie"

CONF_COORDINATOR = "coordinator"


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
