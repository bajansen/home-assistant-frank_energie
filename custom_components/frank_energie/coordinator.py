from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DATA_ELECTRICITY, DATA_GAS, DATA_URL
from .price_data import PriceData

LOGGER = logging.getLogger(__name__)


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
        try:
            data_today = await self._run_graphql_query(today, tomorrow)
            data_tomorrow = await self._run_graphql_query(tomorrow, day_after_tomorrow)
        except UpdateFailed as err:
            # Check if we still have data to work with, if so, return this data. Still log the error as warning
            if self.data[DATA_ELECTRICITY].get_future_prices() and self.data[DATA_GAS].get_future_prices():
                LOGGER.warning(str(err))
                return self.data
            # Re-raise the error if there's no data from future left
            raise err

        return {
            DATA_ELECTRICITY: PriceData(
                data_today.get('marketPricesElectricity', []) + data_tomorrow.get('marketPricesElectricity', [])
            ),
            DATA_GAS: PriceData(
                data_today.get('marketPricesGas', []) + data_tomorrow.get('marketPricesGas', [])
            ),
        }

    async def _run_graphql_query(self, start_date, end_date) -> dict:
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
            return data['data'] if data['data'] else {}

        except (asyncio.TimeoutError, aiohttp.ClientError, KeyError) as error:
            raise UpdateFailed(f"Fetching energy data for period {start_date} - {end_date} failed: {error}") from error
