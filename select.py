"""Select entities for the Grafik Eye 3000 integration."""

from __future__ import annotations

import asyncio

import logging
import re
from signal import SIGPIPE, SIG_DFL, signal
from homeassistant.const import EntityCategory

import telnetlib3
from asyncio import Lock
from telnetlib3 import TelnetReader, TelnetWriter
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from collections.abc import Callable

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
                control_unit["name"],
                control_unit["id"],
                {scene["name"]: str(scene["id"]) for scene in discovery_info["scenes"]},
            )
            for control_unit in discovery_info["control_units"]
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

    _scene_callbacks: dict[int, list[Callable[[str], None]]] = {i+1: [] for i in range(8)}

    STATUS_REGEX = re.compile(r":ss\s([0-9A-FGHMRL]{8,})")

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

        # Start task
        print("Started task")
        asyncio.create_task(self._request_scenes_task())

        # except Exception as e:
        #     LOGGER.error(f"Could not connect to telnet at {self._telnet_host}:{self._telnet_port}: {e}")

    def register_scene_callback(
        self, control_unit_id: int, callback: Callable[[str], None]
    ) -> None:
        """Register a scene callback."""
        self._scene_callbacks[control_unit_id].append(callback)

    async def _request_scenes_task(self) -> None:
        """Continuously request the scene status."""
        while self._ready:
            status = await self._request_scenes()
            for control_unit_id, scene_id in status.items():
                for callback in self._scene_callbacks[control_unit_id]:
                    callback(scene_id)

            await asyncio.sleep(0.5)  # Sleep for 500 milliseconds

    def _send_command(self, command: str) -> None:
        """Send a command to the control unit."""
        if self._ready:
            try:
                self.writer.write(command + "\r\n")
            except Exception as e:
                LOGGER.error(f"Could not execute command: {e}")
                self._ready = False

    def select_scene(self, scene: str, control_units: int | list[int]) -> None:
        """Select a scene on the specified control units."""
        control_units_str = (
            control_units if isinstance(control_units, int) else "".join(control_units)
        )
        self._send_command(f"A{scene}{control_units_str}")

    async def _request_scenes(self) -> dict[int, str] | None:
        """Request the scene status of all control units on the link."""
        self._send_command("G")
        status_bytes = await self.reader.readuntil(b"\r\n")
        status = status_bytes.decode()
        match = self.STATUS_REGEX.search(status)
        if match:
            statuses = match.group(1)  # '000MMMMM'
            # Create a dictionary from control unit numbers to their respective statuses
            control_unit_statuses = {
                (i + 1): status for i, status in enumerate(statuses)
            }
            return control_unit_statuses
        else:
            return None

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

    _control_unit_name: str
    _control_unit_id: int
    _scenes: dict[str, str]

    _lock: Lock

    def __init__(
        self,
        telnet: TelnetConnection,
        control_unit_name: str,
        control_unit_id: int,
        scenes: dict[str, str],
    ) -> None:
        """Initialize the light select entity."""

        self._control_unit_name = control_unit_name
        self._control_unit_id = control_unit_id
        self._scenes = scenes

        self._telnet = telnet
        self._telnet.register_scene_callback(self._control_unit_id, self.async_update_scene)
        self._lock = Lock()

        self.unique_id = f"{DOMAIN}_{control_unit_name.lower()}"
        self._attr_current_option = list(scenes.keys())[0]
        self.entity_description = SelectEntityDescription(
            key=DOMAIN,
            translation_key=DOMAIN,
            name=DISPLAY_NAME.format(control_unit_name=self._control_unit_name),
            entity_category=EntityCategory.CONFIG,
            options=list(scenes.keys()),
        )

    @callback
    def async_update_scene(self, scene_id: str) -> None:
        """Update the selected light value."""
        if not self._lock.locked():  # Check if the lock is not engaged
            scene_id_to_name = {v: k for k, v in self._scenes.items()}
            if scene_id in scene_id_to_name.keys():
                self._attr_current_option = scene_id_to_name[scene_id]
                self.async_write_ha_state()
            else:
                LOGGER.warning("Unsupported scene %s for control unit %d", scene_id, self._control_unit_id)

    async def async_select_option(self, option: str) -> None:
        """Change the selected light value."""
        async with self._lock:  # Engage the lock
            self._telnet._send_command(f"A{self._scenes[option]}{self._control_unit_id}")
            self._attr_current_option = option
            self.async_write_ha_state()
