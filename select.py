"""Select entities for the Grafik Eye 3000 integration."""

from __future__ import annotations

import logging
from signal import SIGPIPE, SIG_DFL, signal
from homeassistant.const import EntityCategory

import telnetlib3
from telnetlib3 import TelnetReader, TelnetWriter
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN, DISPLAY_NAME

LOGGER = logging.getLogger(__package__)

PARALLEL_UPDATES = 0

signal(SIGPIPE, SIG_DFL)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:

    # Connect to GrafikEye 3000 using Telnet
    telnet_connection = TelnetConnection(
        discovery_info.get("host"),
        discovery_info.get("port", None),
        discovery_info.get("login", None),
    )
    await telnet_connection.connect()
    if not telnet_connection._ready:
        return

    add_entities(
        [
            GrafikEye(
                telnet_connection,
                zone["name"],
                zone["id"],
                {scene["name"]: scene["id"] for scene in discovery_info["scenes"]},
            )
            for zone in discovery_info["zones"]
        ]
    )


class TelnetConnection:
    """Telnet connection to a Grafik Eye control unit."""

    reader: TelnetReader
    writer: TelnetWriter

    _host: str
    _port: int
    _login: str

    _ready: bool = False

    def __init__(self, host: str, port: int = 23, login: str = "nwk2") -> None:
        """Initialize Telnet connection to the control unit."""
        self._host = host
        self._port = port
        self._login = login

    async def connect(self):
        """Connect to control unit."""
        # async with self.managed_sigpipe():
        # try:
        self.reader, self.writer = await telnetlib3.open_connection(
            host=self._host, port=self._port, connect_minwait=1.0
        )
        await self.reader.readuntil(b"login: ")
        self.writer.write(self._login + "\r\n")
        res = await self.reader.readuntil(b"connection established\r\n")
        if b"login incorrect" in res or b"connection in use" in res:
            LOGGER.error("Telnet login failed or connection in use")
        else:
            LOGGER.info(f"Connected to GrafikEye using Telnet")
            self._ready = True
        # except Exception as e:
        #     LOGGER.error(f"Could not connect to telnet at {self._telnet_host}:{self._telnet_port}: {e}")

    def _send_command(self, command: str) -> None:
        """Send a command to the control unit."""
        if self._ready:
            try:
                self.writer.write(command + "\r\n")
            except Exception as e:
                LOGGER.error(f"Could not execute command: {e}")
                self._ready = False

    def select_scene(self, scene: str, control_units: str | list[str]) -> None:
        """Select a scene on the specified control units."""
        control_units_str = (
            control_units if isinstance(control_units, str) else "".join(control_units)
        )
        self._send_command(f"A{scene}{control_units_str}")

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
    _zone_id: int
    _scenes: dict[str, int]

    def __init__(
        self,
        telnet: TelnetConnection,
        zone_name: str,
        zone_id: int,
        scenes: dict[str, int],
    ) -> None:
        """Initialize the light select entity."""
        self._telnet = telnet
        self._zone_name = zone_name
        self._zone_id = zone_id
        self._scenes = scenes

        self.unique_id = f"{DOMAIN}_{zone_name.lower()}"
        self._attr_current_option = list(scenes.keys())[0]
        self.entity_description = SelectEntityDescription(
            key=DOMAIN,
            translation_key=DOMAIN,
            name=DISPLAY_NAME.format(zone_name=self._zone_name),
            entity_category=EntityCategory.CONFIG,
            options=list(scenes.keys()),
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected light value."""
        self._telnet._send_command(f"A{self._scenes[option]}{self._zone_id}")
        self._attr_current_option = option
        self.async_write_ha_state()
