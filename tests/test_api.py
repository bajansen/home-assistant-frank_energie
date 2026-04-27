from datetime import date

import pytest
from python_frank_energie.models import Authentication

from custom_components.frank_energie.api import FrankEnergieWithCountry


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def json(self) -> dict:
        return self._payload


class FakeSession:
    def __init__(self, payload: dict) -> None:
        self.calls: list[dict] = []
        self._payload = payload

    async def post(self, url: str, json: dict, headers: dict) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers})
        return FakeResponse(self._payload)


@pytest.mark.asyncio
async def test_prices_request_sends_selected_country_header() -> None:
    session = FakeSession(
        {"data": {"marketPricesElectricity": [], "marketPricesGas": []}}
    )
    api = FrankEnergieWithCountry(clientsession=session, country="BE")

    await api.prices(date(2026, 1, 1), date(2026, 1, 2))

    assert session.calls[0]["headers"]["x-country"] == "BE"
    assert "Authorization" not in session.calls[0]["headers"]


@pytest.mark.asyncio
async def test_authenticated_request_includes_authorization_and_country() -> None:
    session = FakeSession({"data": {}})
    api = FrankEnergieWithCountry(clientsession=session, country="NL")
    api._auth = Authentication("auth-token", "refresh-token")

    await api._query({"query": "query Test { __typename }"})

    assert session.calls[0]["headers"] == {
        "x-country": "NL",
        "Authorization": "Bearer auth-token",
    }
