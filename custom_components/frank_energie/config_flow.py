"""Config flow for Picnic integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (CONF_ACCESS_TOKEN, CONF_AUTHENTICATION,
                                 CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME)
from python_frank_energie import FrankEnergie
from python_frank_energie.exceptions import AuthException

from .const import COMPONENT_TITLE, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Frank Energie."""

    VERSION = 1

    def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_login(self, user_input=None, errors=None):
        """Handle login with credentials by user."""
        if not user_input:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            )

            return self.async_show_form(
                step_id="login",
                data_schema=data_schema,
                errors=errors,
            )

        with FrankEnergie as api:
            try:
                auth = await api.login(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except AuthException:
                return self.async_step_login({"base": "invalid_auth"})

        await self.async_set_unique_id(user_input[CONF_USERNAME])
        self._abort_if_unique_id_configured()

        data = {
            CONF_USERNAME: user_input[CONF_USERNAME],
            CONF_ACCESS_TOKEN: auth.authToken,
            CONF_TOKEN: auth.refreshToken,
        }

        return await self._async_create_entry(data)

    async def async_step_user(self, user_input=None):
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

    async def _async_create_entry(self, data):
        await self.async_set_unique_id(data.get(CONF_USERNAME, "frank_energie"))
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=data.get(CONF_USERNAME, "Frank Energie"), data=data
        )
