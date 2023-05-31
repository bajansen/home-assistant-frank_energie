"""Coordinator implementation for Frank Energie integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, date
from typing import TypedDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from python_frank_energie import FrankEnergie
from python_frank_energie.exceptions import RequestException
from python_frank_energie.models import PriceData, MonthSummary, Invoices, MarketPrices

from .const import DATA_ELECTRICITY, DATA_GAS, DATA_MONTH_SUMMARY, DATA_INVOICES

LOGGER = logging.getLogger(__name__)


class FrankEnergieData(TypedDict):
    DATA_ELECTRICITY: PriceData
    DATA_GAS: PriceData
    DATA_MONTH_SUMMARY: MonthSummary | None
    DATA_INVOICES: Invoices | None


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

    async def _async_update_data(self) -> FrankEnergieData:
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
            prices_today = await self.__fetch_prices_with_fallback(today, tomorrow)
            prices_tomorrow = await self.__fetch_prices_with_fallback(tomorrow, day_after_tomorrow)

            data_month_summary = (
                await self.api.monthSummary() if self.api.is_authenticated else None
            )
            data_invoices = (
                await self.api.invoices() if self.api.is_authenticated else None
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
            DATA_INVOICES: data_invoices,
        }

    async def __fetch_prices_with_fallback(self, start_date: date, end_date: date) -> MarketPrices:
        if not self.api.is_authenticated:
            return await self.api.prices(start_date, end_date)
        else:
            user_prices = await self.api.userPrices(start_date)

            if len(user_prices.gas.all) > 0 and len(user_prices.electricity.all) > 0:
                # If user_prices are available for both gas and electricity return them
                return user_prices
            else:
                public_prices = await self.api.prices(start_date, end_date)

                # Use public prices if no user prices are available
                if len(user_prices.gas.all) == 0:
                    LOGGER.info("No gas prices found for user, falling back to public prices")
                    user_prices.gas = public_prices.gas

                if len(user_prices.electricity.all) == 0:
                    LOGGER.info("No electricity prices found for user, falling back to public prices")
                    user_prices.electricity = public_prices.electricity

                return user_prices

