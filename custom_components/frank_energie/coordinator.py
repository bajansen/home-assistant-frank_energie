"""Coordinator implementation for Frank Energie integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from python_frank_energie import FrankEnergie

from .const import DATA_ELECTRICITY, DATA_GAS, DATA_MONTH_SUMMARY

LOGGER = logging.getLogger(__name__)


class FrankEnergieCoordinator(DataUpdateCoordinator):
    """Get the latest data and update the states."""

    api: FrankEnergie

    def __init__(self, hass: HomeAssistant, api: FrankEnergie) -> None:
        """Initialize the data object."""
        self.hass = hass
        self.api = api

        logger = logging.getLogger(__name__)
        super().__init__(
            hass,
            logger,
            name="Frank Energie coordinator",
            update_interval=timedelta(minutes=60),
        )

    async def _async_update_data(self) -> dict:
        """Get the latest data from Frank Energie."""
        self.logger.debug("Fetching Frank Energie data")

        # We request data for today up until the day after tomorrow.
        # This is to ensure we always request all available data.
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        day_after_tomorrow = today + timedelta(days=2)

        # Fetch data for today and tomorrow separately,
        # because the gas prices response only contains data for the first day of the query
        try:
            (data_today_electricity, data_today_gas) = await self.api.prices(
                today, tomorrow
            )
            (data_tomorrow_electricity, data_tomorrow_gas) = await self.api.prices(
                tomorrow, day_after_tomorrow
            )
        except UpdateFailed as err:
            # Check if we still have data to work with, if so, return this data. Still log the error as warning
            if (
                self.data[DATA_ELECTRICITY].get_future_prices()
                and self.data[DATA_GAS].get_future_prices()
            ):
                LOGGER.warning(str(err))
                return self.data
            # Re-raise the error if there's no data from future left
            raise err

        data_month_summary = (
            await self.api.monthSummary() if self.api.is_authenticated else None
        )

        return {
            DATA_ELECTRICITY: data_today_electricity + data_tomorrow_electricity,
            DATA_GAS: data_today_gas + data_tomorrow_gas,
            DATA_MONTH_SUMMARY: data_month_summary,
        }
