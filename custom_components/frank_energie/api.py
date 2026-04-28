"""Frank Energie API client extensions for Home Assistant."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from aiohttp.client import ClientError, ClientSession
from python_frank_energie import FrankEnergie
from python_frank_energie.exceptions import AuthException, AuthRequiredException

from .const import DEFAULT_COUNTRY, SUPPORTED_COUNTRIES


@dataclass
class FrankUserSite:
    """User site details used by integration setup."""

    reference: str
    status: str | None
    address_street: str | None
    address_houseNumber: str | None
    address_houseNumberAddition: str | None
    address_zipCode: str | None
    address_city: str | None


class FrankEnergieWithCountry(FrankEnergie):
    """FrankEnergie client that always sends the selected country header."""

    def __init__(
        self,
        clientsession: ClientSession = None,
        auth_token: str | None = None,
        refresh_token: str | None = None,
        country: str = DEFAULT_COUNTRY,
    ) -> None:
        super().__init__(
            clientsession=clientsession,
            auth_token=auth_token,
            refresh_token=refresh_token,
        )
        country = country.upper()
        self._country = country if country in SUPPORTED_COUNTRIES else DEFAULT_COUNTRY

    async def _query(self, query):
        """Run GraphQL query with auth and selected country headers."""
        if self._session is None:
            self._session = ClientSession()
            self._close_session = True

        headers = {"x-country": self._country}
        if self._auth is not None:
            headers["Authorization"] = f"Bearer {self._auth.authToken}"

        try:
            resp = await self._session.post(
                self.DATA_URL,
                json=query,
                headers=headers,
            )
            response = await resp.json()
        except (asyncio.TimeoutError, ClientError, KeyError) as error:
            raise ValueError(f"Request failed: {error}") from error

        if errors := response.get("errors"):
            for error in errors:
                if error["message"] == "user-error:auth-not-authorised":
                    raise AuthException

        return response

    async def user_sites(self) -> list[FrankUserSite]:
        """Get user sites using a query compatible with current Frank API."""
        if self._auth is None:
            raise AuthRequiredException

        response = await self._query(
            {
                "query": """
                    query UserSites {
                        userSites {
                            reference
                            status
                            address {
                                street
                                houseNumber
                                houseNumberAddition
                                zipCode
                                city
                            }
                        }
                    }
                """,
                "operationName": "UserSites",
                "variables": {},
            }
        )

        sites = response.get("data", {}).get("userSites", []) if isinstance(response, dict) else []
        result: list[FrankUserSite] = []
        for site in sites:
            address = site.get("address") or {}
            result.append(
                FrankUserSite(
                    reference=site.get("reference"),
                    status=site.get("status"),
                    address_street=address.get("street"),
                    address_houseNumber=address.get("houseNumber"),
                    address_houseNumberAddition=address.get("houseNumberAddition"),
                    address_zipCode=address.get("zipCode"),
                    address_city=address.get("city"),
                )
            )

        return [site for site in result if site.reference]
