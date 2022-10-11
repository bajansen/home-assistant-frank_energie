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
ATTR_HOUR = "Hour"
ATTR_TIME = "Time"

@dataclass
class FrankEnergieEntityDescription(SensorEntityDescription):
    """Describes Frank Energie sensor entity."""
    value_fn: Callable[[dict], StateType] = None
    attr_fn: Callable[[dict[str, Any]], dict[str, StateType]] = lambda _: {}

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
        key="elec_tax_vat",
        name="Current electricity VAT price",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        value_fn=lambda data: data['elec'][1],
        entity_registry_enabled_default=False,
    ),
        FrankEnergieEntityDescription(
        key="elec_sourcing",
        name="Current electricity sourcing markup",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        value_fn=lambda data: data['elec'][2],
        entity_registry_enabled_default=False,
    ),
        FrankEnergieEntityDescription(
        key="elec_tax_only",
        name="Current electricity tax only",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        value_fn=lambda data: data['elec'][3],
        entity_registry_enabled_default=False,
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
        key="gas_tax_vat",
        name="Current gas VAT price",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
        value_fn=lambda data: data['gas'][1],
        entity_registry_enabled_default=False,
    ),
    FrankEnergieEntityDescription(
        key="gas_sourcing",
        name="Current gas sourcing price",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
        value_fn=lambda data: data['gas'][2],
        entity_registry_enabled_default=False,
    ),
    FrankEnergieEntityDescription(
        key="gas_tax_only",
        name="Current gas tax only",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
        value_fn=lambda data: data['gas'][3],
        entity_registry_enabled_default=False,
    ),
    FrankEnergieEntityDescription(
        key="gas_min",
        name="Lowest gas price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
        value_fn=lambda data: min(data['today_gas']),
        attr_fn=lambda data: {ATTR_HOUR: data['today_gas'].index(min(data['today_gas'])),ATTR_TIME:datetime.now().replace(hour=data['today_gas'].index(min(data['today_gas'])), minute=0, second=0, microsecond=0)},
    ),
    FrankEnergieEntityDescription(
        key="gas_max",
        name="Highest gas price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
        value_fn=lambda data: max(data['today_gas']),
        attr_fn=lambda data: {ATTR_HOUR: data['today_gas'].index(max(data['today_gas'])),ATTR_TIME:datetime.now().replace(hour=data['today_gas'].index(max(data['today_gas'])), minute=0, second=0, microsecond=0)},
    ),
    FrankEnergieEntityDescription(
        key="elec_min",
        name="Lowest energy price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        value_fn=lambda data: min(data['today_elec']),
        attr_fn=lambda data: {ATTR_HOUR: data['today_elec'].index(min(data['today_elec'])),ATTR_TIME:datetime.now().replace(hour=data['today_elec'].index(min(data['today_elec'])), minute=0, second=0, microsecond=0)},
    ),
    FrankEnergieEntityDescription(
        key="elec_max",
        name="Highest energy price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        value_fn=lambda data: max(data['today_elec']),
        attr_fn=lambda data: {ATTR_HOUR: data['today_elec'].index(max(data['today_elec'])),ATTR_TIME:datetime.now().replace(hour=data['today_elec'].index(max(data['today_elec'])), minute=0, second=0, microsecond=0)},
    ),
    FrankEnergieEntityDescription(
        key="elec_avg",
        name="Average electricity price today",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        value_fn=lambda data: round(sum(data['today_elec']) / len(data['today_elec']), 5)
    ),
)
