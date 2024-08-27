"""Select entities for the Grafik Eye 3000 integration."""

from __future__ import annotations

import logging
from asyncio import Lock
from datetime import datetime

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DISPLAY_NAME, DOMAIN, PROCESSING_TIME_IGNORE_CALLBACK
from .grafik_eye import GrafikEyeController

_LOGGER = logging.getLogger(__package__)

PARALLEL_UPDATES = 0


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:

    # Connect to GrafikEye 3000 using Telnet
    grafik_eye = GrafikEyeController(
        discovery_info.get("host"),
        **{k: v for k, v in discovery_info.items() if k in ["port", "login"]},
    )
    await grafik_eye.connect()

    add_entities(
        [
            GrafikEyeSceneSelectEntity(
                grafik_eye,
                control_unit["name"],
                control_unit["id"],
                {scene["name"]: str(scene["id"]) for scene in discovery_info["scenes"]},
            )
            for control_unit in discovery_info["control_units"]
        ]
    )


class GrafikEyeSceneSelectEntity(SelectEntity):
    """Representation of a light select entity."""

    _grafik_eye: GrafikEyeController

    _control_unit_name: str
    _control_unit_id: int
    _scenes: dict[str, str]

    _lock: Lock
    _last_select: datetime = datetime.now()

    def __init__(
        self,
        grafik_eye: GrafikEyeController,
        control_unit_name: str,
        control_unit_id: int,
        scenes: dict[str, str],
    ) -> None:
        """Initialize the light select entity."""
        self._control_unit_name = control_unit_name
        self._control_unit_id = control_unit_id
        self._scenes = scenes

        self._grafik_eye = grafik_eye
        self._grafik_eye.register_scene_callback(
            self._control_unit_id, self.async_update_scene
        )
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
            if datetime.now() - self._last_select < PROCESSING_TIME_IGNORE_CALLBACK:
                return

            scene_id_to_name = {v: k for k, v in self._scenes.items()}
            if scene_id in scene_id_to_name.keys():
                self._attr_current_option = scene_id_to_name[scene_id]
                self.async_write_ha_state()
            else:
                _LOGGER.warning(
                    "(%s:%d) Unsupported scene %s for control unit %d",
                    self._grafik_eye._host,
                    self._grafik_eye._port,
                    scene_id,
                    self._control_unit_id,
                )

    async def async_select_option(self, option: str) -> None:
        """Change the selected light value."""
        async with self._lock:  # Engage the lock
            self._grafik_eye._send_command(
                f"A{self._scenes[option]}{self._control_unit_id}"
            )
            self._attr_current_option = option
            self.async_write_ha_state()
            self._last_select = datetime.now()
