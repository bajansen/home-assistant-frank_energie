from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt
from .const import DATA_URL


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
            update_interval=timedelta(minutes=60),
        )

    async def _async_update_data(self) -> dict:
        """Get the latest data from Frank Energie"""
        self.logger.debug("Fetching Frank Energie data")

        # We request data for today up until the day after tomorrow.
        # This is to ensure we always request all available data.
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        day_after_tomorrow = today + timedelta(days=2)

        # Fetch data for today and tomorrow separately,
        # because the gas prices response only contains data for the first day of the query
        data_today = await self._run_graphql_query(today, tomorrow)
        data_tomorrow = await self._run_graphql_query(tomorrow, day_after_tomorrow)

        return {
            'marketPricesElectricity': data_today['marketPricesElectricity'] + data_tomorrow['marketPricesElectricity'],
            'marketPricesGas': data_today['marketPricesGas'] + data_tomorrow['marketPricesGas'],
        }

    async def _run_graphql_query(self, start_date, end_date):
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
            "variables": {"startDate": str(start_date), "endDate": str(end_date)},
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

    def get_hourprices(self, hourprices) -> Dict:
        today_prices = dict()
        for hour in hourprices:
            # Calling astimezone(None) automagically gets local timezone
            fromtime = dt.parse_datetime(hour['from']).astimezone()
            today_prices[fromtime] = hour['marketPrice'] + hour['marketPriceTax'] + hour['sourcingMarkupPrice'] + hour['energyTaxPrice']
        return today_prices
