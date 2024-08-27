"""Grafik Eye integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType

from .const import *


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Your controller/hub specific code."""

    hass.async_create_task(
        async_load_platform(hass, "select", DOMAIN, config[DOMAIN], config)
    )

    return True
