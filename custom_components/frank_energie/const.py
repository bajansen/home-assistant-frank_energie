"""Constants for the Frank Energie integration."""
from __future__ import annotations

ATTRIBUTION = "Data provided by Frank Energie"
DOMAIN = "frank_energie"
DATA_URL = "https://frank-graphql-prod.graphcdn.app/"
ICON = "mdi:currency-eur"
UNIQUE_ID = f"{DOMAIN}_component"
COMPONENT_TITLE = "Frank Energie"

CONF_COORDINATOR = "coordinator"
ATTR_TIME = "from_time"

DATA_ELECTRICITY = "electricity"
DATA_GAS = "gas"
DATA_MONTH_SUMMARY = "month_summary"
