"""Config flow for Frank Energie integration."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_AUTHENTICATION,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_USERNAME,
)
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
from python_frank_energie import FrankEnergie
from python_frank_energie.exceptions import AuthException

from .const import DOMAIN, CONF_SITE

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Frank Energie."""

    VERSION = 1
    sign_in_data = {}

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._reauth_entry = None

    async def async_step_login(self, user_input=None, errors=None) -> FlowResult:
        """Handle login with credentials by user."""
        if not user_input:
            username = (
                self._reauth_entry.data[CONF_USERNAME] if self._reauth_entry else None
            )

            data_schema = vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=username): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            )

            return self.async_show_form(
                step_id="login",
                data_schema=data_schema,
                errors=errors,
            )

        async with FrankEnergie() as api:
            try:
                auth = await api.login(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except AuthException as ex:
                _LOGGER.exception("Error during login", exc_info=ex)
                return await self.async_step_login(errors={"base": "invalid_auth"})

        self.sign_in_data = {
            CONF_USERNAME: user_input[CONF_USERNAME],
            CONF_ACCESS_TOKEN: auth.authToken,
            CONF_TOKEN: auth.refreshToken
        }

        if self._reauth_entry:
            self.hass.config_entries.async_update_entry(
                self._reauth_entry,
                data=self.sign_in_data,
            )

            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
            )

            return self.async_abort(reason="reauth_successful")

        return await self.async_step_site(self.sign_in_data)

    async def async_step_site(self, user_input=None, errors=None) -> FlowResult:
        """Handle possible multi site accounts."""
        if user_input.get(CONF_SITE) is None:
            api = FrankEnergie(
                auth_token=self.sign_in_data.get(CONF_ACCESS_TOKEN, None),
                refresh_token=self.sign_in_data.get(CONF_TOKEN, None),
            )
            me = await api.me()

            # filter out all sites that are not in delivery
            me.deliverySites = [site for site in me.deliverySites if site.status == "IN_DELIVERY"]

            if len(me.deliverySites) == 0:
                raise Exception("No suitable sites found for this account")

            site_options = [{"value": site.reference, "label": self.create_title(site)} for site in me.deliverySites]
            default_site = me.deliverySites[0].reference

            options = {vol.Required(CONF_SITE, default=default_site): SelectSelector(SelectSelectorConfig(
                options=site_options,
                mode=SelectSelectorMode.LIST,
            ))}

            return self.async_show_form(
                step_id="site", data_schema=vol.Schema(options), errors=errors
            )

        self.sign_in_data[CONF_SITE] = user_input[CONF_SITE]

        return await self._async_create_entry(self.sign_in_data)

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle a flow initiated by the user."""
        if not user_input:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_AUTHENTICATION): bool,
                }
            )

            return self.async_show_form(step_id="user", data_schema=data_schema)

        if user_input[CONF_AUTHENTICATION]:
            return await self.async_step_login()

        data = {}

        return await self._async_create_entry(data)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle configuration by re-auth."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_login()

    async def _async_create_entry(self, data):
        unique_id = data[CONF_SITE] + data[CONF_USERNAME]
        await self.async_set_unique_id(unique_id)
        # await self.async_set_unique_id(data.get(CONF_USERNAME, "frank_energie"))
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=data.get(CONF_USERNAME, "Frank Energie"), data=data
        )

    @staticmethod
    def create_title(site) -> str:
        title = f"{site.address_street} {site.address_houseNumber}"
        if site.address_houseNumberAddition is not None:
            title += f" {site.address_houseNumberAddition}"

        return title
