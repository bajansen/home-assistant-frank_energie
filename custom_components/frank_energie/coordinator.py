"""Coordinator implementation for Frank Energie integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from python_frank_energie import FrankEnergie
from python_frank_energie.exceptions import RequestException

from .const import DATA_ELECTRICITY, DATA_GAS, DATA_MONTH_SUMMARY

LOGGER = logging.getLogger(__name__)


class FrankEnergieCoordinator(DataUpdateCoordinator):
    """Get the latest data and update the states."""

    api: FrankEnergie

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: FrankEnergie
    ) -> None:
        """Initialize the data object."""
        self.hass = hass
        self.entry = entry
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
            prices_today = await self.api.prices(today, tomorrow)
            prices_tomorrow = await self.api.prices(tomorrow, day_after_tomorrow)
            data_month_summary = (
                await self.api.monthSummary() if self.api.is_authenticated else None
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
        except RequestException as ex:
            if str(ex).startswith("user-error:"):
                raise ConfigEntryAuthFailed from ex

            raise UpdateFailed(ex) from ex

        return {
            DATA_ELECTRICITY: prices_today.electricity + prices_tomorrow.electricity,
            DATA_GAS: prices_today.gas + prices_tomorrow.gas,
            DATA_MONTH_SUMMARY: data_month_summary,
        }
