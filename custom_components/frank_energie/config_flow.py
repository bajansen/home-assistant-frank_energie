"""Config flow for Picnic integration."""
from __future__ import annotations

import logging

from homeassistant import config_entries
from .const import COMPONENT_TITLE, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Frank Energie."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle adding the config, no user input is needed."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title=COMPONENT_TITLE, data={})

        return self.async_show_form(step_id="user")
