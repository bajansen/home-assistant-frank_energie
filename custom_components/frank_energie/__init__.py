"""The Frank Energie component."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, Platform, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FrankEnergieWithCountry
from .const import CONF_COORDINATOR, CONF_COUNTRY, DEFAULT_COUNTRY, DOMAIN
from .coordinator import FrankEnergieCoordinator

LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Frank Energie component from a config entry."""

    # For backwards compatibility, set unique ID
    if entry.unique_id is None or entry.unique_id == "frank_energie_component":
        hass.config_entries.async_update_entry(entry, unique_id=str("frank_energie"))

    country = entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY)

    # Select site-reference, or find first one that has status 'IN_DELIVERY' if not set
    if entry.data.get("site_reference") is None and entry.data.get(CONF_ACCESS_TOKEN) is not None:
        api = FrankEnergieWithCountry(
            clientsession=async_get_clientsession(hass),
            auth_token=entry.data.get(CONF_ACCESS_TOKEN, None),
            refresh_token=entry.data.get(CONF_TOKEN, None),
            country=country,
        )
        sites = await api.user_sites()
        in_delivery_sites = [site for site in sites if site.status == "IN_DELIVERY"]
        site = in_delivery_sites[0] if in_delivery_sites else sites[0] if sites else None

        if site is None:
            raise Exception("No suitable sites found for this account")

        if site.status != "IN_DELIVERY":
            LOGGER.info("No IN_DELIVERY site found; using first available site: %s", site.reference)

        hass.config_entries.async_update_entry(entry, data={**entry.data, "site_reference": site.reference})

        # Update title
        street = site.address_street or "Frank Energie"
        house_number = site.address_houseNumber or ""
        title = f"{street} {house_number}".strip()
        if site.address_houseNumberAddition is not None:
            title += f" {site.address_houseNumberAddition}"
        hass.config_entries.async_update_entry(entry, title=title)

    # Initialise the coordinator and save it as domain-data
    api = FrankEnergieWithCountry(
        clientsession=async_get_clientsession(hass),
        auth_token=entry.data.get(CONF_ACCESS_TOKEN, None),
        refresh_token=entry.data.get(CONF_TOKEN, None),
        country=country,
    )
    frank_coordinator = FrankEnergieCoordinator(hass, entry, api)

    # Fetch initial data, so we have data when entities subscribe and set up the platform
    await frank_coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_COORDINATOR: frank_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
