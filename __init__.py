"""The Saavn integration."""

import voluptuous as vol
import logging
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import discovery

from .const import DATA_SAAVN_CLIENT, DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    hass.async_create_task(
    discovery.async_load_platform(
        hass, MEDIA_PLAYER_DOMAIN, DOMAIN, {}, config
    )
    )

    # Return boolean to indicate that initialization was successful.
    return True
