"""The Frank Energie component."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, Platform, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from python_frank_energie import FrankEnergie

from .const import CONF_COORDINATOR, DOMAIN
from .coordinator import FrankEnergieCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Frank Energie component from a config entry."""

    # For backwards compatibility, set unique ID
    if entry.unique_id is None or entry.unique_id == "frank_energie_component":
        hass.config_entries.async_update_entry(entry, unique_id=str("frank_energie"))

    # Select site-reference, or find first one that has status 'IN_DELIVERY' if not set
    if entry.data.get("site_reference") is None and entry.data.get(CONF_ACCESS_TOKEN) is not None:
        api = FrankEnergie(
            clientsession=async_get_clientsession(hass),
            auth_token=entry.data.get(CONF_ACCESS_TOKEN, None),
            refresh_token=entry.data.get(CONF_TOKEN, None),
        )
        me = await api.me()

        # filter out all sites that are not in delivery
        me.deliverySites = [site for site in me.deliverySites if site.status == "IN_DELIVERY"]

        if len(me.deliverySites) == 0:
            raise Exception("No suitable sites found for this account")

        site = me.deliverySites[0]
        hass.config_entries.async_update_entry(entry, data={**entry.data, "site_reference": site.reference})

        # Update title
        title = f"{site.address_street} {site.address_houseNumber}"
        if site.address_houseNumberAddition is not None:
            title += f" {site.address_houseNumberAddition}"
        hass.config_entries.async_update_entry(entry, title=title)

    # Initialise the coordinator and save it as domain-data
    api = FrankEnergie(
        clientsession=async_get_clientsession(hass),
        auth_token=entry.data.get(CONF_ACCESS_TOKEN, None),
        refresh_token=entry.data.get(CONF_TOKEN, None),
    )
    frank_coordinator = FrankEnergieCoordinator(hass, entry, api, entry.data.get("site_reference", None))

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
