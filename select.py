from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from signal import SIGPIPE, SIG_DFL, signal
from homeassistant.const import EntityCategory

import telnetlib3
from telnetlib3 import TelnetReader, TelnetWriter
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

LOGGER = logging.getLogger(__package__)
signal(
    SIGPIPE, SIG_DFL
)  # Setting at the module level, consider managing locally if needed elsewhere


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    if discovery_info is None:
        return

    telnet_connection = TelnetConnection(discovery_info)
    await telnet_connection.connect()
    if not telnet_connection.ready:
        return

    grafik_eyes = []
    for zone in discovery_info["zones"]:
        grafik_eyes.append(
            GrafikEye(
                telnet_connection,
                zone["name"],
                zone["code"],
                {scene["name"]: scene["code"] for scene in discovery_info["scenes"]},
            )
        )

    add_entities(grafik_eyes)


class TelnetConnection:

    reader: TelnetReader
    writer: TelnetWriter

    def __init__(self, info) -> None:
        self.ready = False
        self._telnet_host = info.get("ip", "192.168.178.14")
        self._telnet_port = info.get("port", 23)
        self._telnet_login: str = info.get("login", "nwk2")

    async def connect(self):
        # async with self.managed_sigpipe():
        # try:
        self.reader, self.writer = await telnetlib3.open_connection(
            host=self._telnet_host, port=self._telnet_port, connect_minwait=1.0
        )
        await self.login()
        # except Exception as e:
        #     LOGGER.error(f"Could not connect to telnet at {self._telnet_host}:{self._telnet_port}: {e}")

    async def login(self):
        # try:
        await self.reader.readuntil(b"login: ")
        self.writer.write(self._telnet_login + "\r\n")
        res = await self.reader.readuntil(b"connection established\r\n")
        if b"login incorrect" in res or b"connection in use" in res:
            LOGGER.error("Telnet login failed or connection in use")
        else:
            LOGGER.info(f"Connected to GrafikEye using Telnet")
            self.ready = True
        # except Exception as e:
        #     LOGGER.error(f"Could not login with login code {self._telnet_login}: {e}")

    def execute(self, command: str):
        if self.ready:
            try:
                self.writer.write(command + "\r\n")
            except Exception as e:
                LOGGER.error(f"Could not execute command: {e}")
                self.ready = False

    # @asynccontextmanager
    # async def managed_sigpipe(self):
    #     old_handler = signal.getsignal(SIGPIPE)
    #     signal.signal(SIGPIPE, SIG_DFL)
    #     try:
    #         yield
    #     finally:
    #         signal.signal(SIGPIPE, old_handler)


class GrafikEye(SelectEntity):
    """Representation of a light select entity."""

    _telnet: TelnetConnection

    _zone_name: str
    _zone_code: int
    _scenes: dict[str, int]

    def __init__(
        self, telnet: TelnetConnection, zone_name: str, zone_code: int, scenes: dict[str, int]
    ) -> None:
        """Initialize the light select entity."""
        self._telnet = telnet
        self._zone_name = zone_name
        self._zone_code = zone_code
        self._scenes = scenes

        self.unique_id = f"grafik_eye_{zone_name.lower()}"
        self._attr_current_option = list(scenes.keys())[0]
        self.entity_description = SelectEntityDescription(
            key="grafik_eye",
            name=f"Grafik Eye 3000: {self._zone_name}",
            entity_category=EntityCategory.CONFIG,
            icon="mdi:lightbulb",
            options=list(scenes.keys()),
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected light value."""
        self._telnet.execute(
            f"A{self._scenes[option]}{self._zone_code}"
        )
        self._attr_current_option = option
        self.async_write_ha_state()
