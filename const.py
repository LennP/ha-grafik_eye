"""Constants for Grafik Eye 3000 integration."""

from __future__ import annotations

from datetime import timedelta

CONF_LOGIN = "login"
CONF_CONTROL_UNITS = "control_units"
CONF_SCENES = "scenes"

DOMAIN = "grafik_eye"
DISPLAY_NAME = "Grafik Eye 3000: {control_unit_name}"

UPDATE_INTERVAL = timedelta(milliseconds=500)
PROCESSING_TIME_IGNORE_CALLBACK = timedelta(seconds=1)
