"""Grafik Eye 3000 integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Grafik Eye 3000 integration."""

    hass.async_create_task(
        async_load_platform(hass, Platform.SELECT, DOMAIN, config[DOMAIN], config)
    )

    return True
