"""Grafik Eye."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable
from signal import SIG_DFL, SIGPIPE, signal

import telnetlib3
from telnetlib3 import TelnetReader, TelnetWriter

from .const import UPDATE_INTERVAL

_LOGGER = logging.getLogger(__package__)

signal(SIGPIPE, SIG_DFL)


class GrafikEyeController:
    """Telnet connection to a Grafik Eye."""

    reader: TelnetReader
    writer: TelnetWriter

    _host: str
    _port: int
    _login: str

    _scene_callbacks: dict[int, list[Callable[[str], None]]] = {
        i + 1: [] for i in range(8)
    }

    STATUS_REGEX = re.compile(r":ss\s([0-9A-FGHMRL]{8,})")

    def __init__(self, host: str, port: int = 23, login: str = "nwk2") -> None:
        """Initialize Telnet connection to the Grafik Eye."""
        self._host = host
        self._port = port
        self._login = login

    async def connect(self):
        """Connect to the Grafik Eye."""
        self.reader, self.writer = await telnetlib3.open_connection(
            host=self._host, port=self._port, connect_minwait=1.0
        )
        await self.reader.readuntil(b"login: ")
        self.writer.write(self._login + "\r\n")
        res = await self.reader.readuntil(b"connection established\r\n")
        if b"login incorrect" in res:
            _LOGGER.error("(%s:%d) Grafik Eye controller login incorrect", self._host, self._port)
        elif b"connection in use" in res:
            _LOGGER.error("(%s:%d) Grafik Eye controller login in use", self._host, self._port)
        else:
            _LOGGER.info("(%s:%d) Connected to Grafik Eye controller", self._host, self._port)

        # Start task
        asyncio.create_task(self._request_scenes_task())

    def select_scene(self, scene: str, control_units: int | list[int]) -> None:
        """Select a scene on the specified control units."""
        control_units_str = (
            control_units if isinstance(control_units, int) else "".join(control_units)
        )
        self._send_command(f"A{scene}{control_units_str}")

    def register_scene_callback(
        self, control_unit_id: int, scene_callback: Callable[[str], None]
    ) -> None:
        """Register a scene callback."""
        self._scene_callbacks[control_unit_id].append(scene_callback)

    async def _request_scenes_task(self) -> None:
        """Continuously request the scene status."""
        while True:
            status = await self._request_scenes()
            if status:
                for control_unit_id, scene_id in status.items():
                    for scene_callback in self._scene_callbacks[control_unit_id]:
                        scene_callback(scene_id)
            await asyncio.sleep(UPDATE_INTERVAL.total_seconds())

    async def _request_scenes(self) -> dict[int, str] | None:
        """Request the scene status of all control units on the link."""
        self._send_command("G")
        status_bytes = await self.reader.readuntil(b"\r\n")
        await self.reader.read(len(self.reader._buffer))
        status = status_bytes.decode()
        match = self.STATUS_REGEX.search(status)
        if match:
            statuses = match.group(1)  # '000MMMMM'
            # Create a dictionary from control unit ids to their respective scenes
            control_unit_statuses = {
                (i + 1): status for i, status in enumerate(statuses)
            }
            return control_unit_statuses
        else:
            return None

    def _send_command(self, command: str) -> None:
        """Send a command to the control unit."""
        try:
            self.writer.write(command + "\r\n")
        except Exception as e:
            _LOGGER.error(
                "(%s:%d) Error executing command %s: %s",
                self._host,
                self._port,
                command,
                e,
            )
            raise e
