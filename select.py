"""Platform for sensor integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from telnetlib import Telnet
from signal import SIGPIPE, SIG_DFL, signal

from .const import *

signal(SIGPIPE, SIG_DFL)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor pl atform."""
    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    # Create one telnet connection
    telnet_connection = TelnetConnection(discovery_info)
    if not telnet_connection.ready:
        return

    grafik_eyes = []

    for zone in discovery_info["zones"]:
        grafik_eyes.append(GrafikEye(telnet_connection, zone, discovery_info["scenes"]))

    add_entities(grafik_eyes)


class TelnetConnection:
    """Telnet Connection"""

    def __init__(self, info) -> None:
        self.ready = False

        self._telnet_host = info.get("ip") or "192.168.178.14"
        self._telnet_port = info.get("port") or 23
        self._telnet_login = info.get("login") or "nwk2"
        self._telnet_timeout = 5

        self.connect()

    def connect(self) -> None:
        try:
            self._connection = Telnet(
                self._telnet_host, self._telnet_port, self._telnet_timeout
            )
            self.login()

        except:
            LOGGER.error(
                f"Could not connect to telnet at {self._telnet_host}:{self._telnet_port}"
            )
            print(
                f"Could not connect to telnet at {self._telnet_host}:{self._telnet_port}"
            )

    def login(self) -> None:
        try:
            self._connection.read_until(b"login: ", 3)
            self._connection.write(str(self._telnet_login + "\r\n").encode("ascii"))
            res = self._connection.read_until(b"connection established\r\n", 1)
            if res == b"\r\nlogin incorrect\r\n\r\nlogin: ":
                LOGGER.error("Telnet login incorrect")
            elif res == b"\r\nconnection in use\r\n\r\nlogin: ":
                LOGGER.error("Telnet connection already in use")
            else:
                self.ready = True
        except:
            LOGGER.error(f"Could not login with login code {self._telnet_login}")

    def execute(self, command: str) -> None:
        try:
            print("executing " + str((command + "\r\n").encode("ascii")))
            self._connection.write((command + "\r\n").encode("ascii"))
        except OSError:
            LOGGER.error("Could not execute command: connection closed")


class GrafikEye(SelectEntity):
    """Grafik Eye 3000 Component"""

    def __init__(self, telnet: TelnetConnection, zone, scenes) -> None:
        """Initialize the sensor."""
        self._zonename = zone["name"]
        self._zonecode = zone["code"]

        self._attr_current_option = "Scene 1"
        self._attr_options = [x["name"] for x in scenes]
        self._scenecodes = [x["code"] for x in scenes]

        self._telnet = telnet

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"Grafik Eye 3000: {self._zonename}"

    def select_option(self, option: str) -> None:
        """Change selected option"""
        self._telnet.execute(
            f"A{self._scenecodes[self._attr_options.index(option)]}{self._zonecode}"
        )
