"""Grafik Eye 3000 integration."""

from __future__ import annotations

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_HOST, CONF_ID, CONF_NAME, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType

from .const import CONF_CONTROL_UNITS, CONF_LOGIN, CONF_SCENES, DOMAIN

CONTROL_UNIT_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ID): cv.positive_int,
})

SCENE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ID): cv.positive_int,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT): cv.positive_int,
        vol.Optional(CONF_LOGIN): cv.string,
        vol.Required(CONF_CONTROL_UNITS): vol.All(cv.ensure_list, [CONTROL_UNIT_SCHEMA]),
        vol.Required(CONF_SCENES): vol.All(cv.ensure_list, [SCENE_SCHEMA]),
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Grafik Eye 3000 integration."""

    hass.async_create_task(
        async_load_platform(hass, Platform.SELECT, DOMAIN, config[DOMAIN], config)
    )

    return True
