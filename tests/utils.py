from datetime import datetime, timedelta
from http import HTTPStatus

from homeassistant.const import CONTENT_TYPE_JSON
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMockResponse,
)

from custom_components.frank_energie import const


class ResponseMocks:
    """Simple iterator to iterate through a set of responses."""

    def __init__(self):
        self._responses = []
        self._index = 0
        self._cyclic = False

    def __iter__(self):
        return self

    def __next__(self):
        if self._index < len(self._responses):
            response = self._responses[self._index]
            self._index += 1
            if self._cyclic:
                self._index %= len(self._responses)
            return response

        raise StopIteration

    def cyclic(self):
        """Makes the iterator cycle endlessly through the set responses."""
        self._cyclic = True

    def add(
        self,
        start_date: datetime,
        electricity_prices: list,
        gas_prices: list,
        http_status: int = HTTPStatus.OK,
    ):
        """Add a response mock."""
        self._responses.append(
            AiohttpClientMockResponse(
                "POST",
                const.DATA_URL,
                json={
                    "data": {
                        "marketPricesElectricity": self._generate_prices_response(
                            start_date, electricity_prices
                        ),
                        "marketPricesGas": self._generate_prices_response(
                            start_date, gas_prices
                        ),
                    }
                },
                headers={"Content-Type": CONTENT_TYPE_JSON},
                status=http_status,
            )
        )

    def _generate_prices_response(self, start: datetime, all_in_prices: list | range):
        """Generate a list of prices."""
        start = start.replace(second=0, microsecond=0)
        return [
            {
                "from": (start + timedelta(hours=i)).astimezone().isoformat(),
                "till": (start + timedelta(hours=i + 1)).astimezone().isoformat(),
                "marketPrice": 0.7 * price,
                "marketPriceTax": 0.05 * price,
                "sourcingMarkupPrice": 0.1 * price,
                "energyTaxPrice": 0.15 * price,
            }
            for i, price in enumerate(all_in_prices)
        ]
