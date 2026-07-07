"""Finds the Andon Light's USB serial port."""

from __future__ import annotations

import os
from dataclasses import dataclass

from serial.tools import list_ports

# arduino-pico's default TinyUSB descriptor keeps the Raspberry Pi Foundation
# vendor ID. Confirmed correct (2026-07-07) against the real Waveshare
# RP2040-Zero via `udevadm info` and `andon-light doctor`.
DEFAULT_VID = 0x2E8A

ENV_PORT_OVERRIDE = "ANDON_LIGHT_PORT"


@dataclass
class DiscoveryResult:
    port: str | None
    candidates: list[str]


def find_device_port() -> DiscoveryResult:
    override = os.environ.get(ENV_PORT_OVERRIDE)
    if override:
        return DiscoveryResult(port=override, candidates=[override])

    candidates = [p.device for p in list_ports.comports() if p.vid == DEFAULT_VID]
    if len(candidates) == 1:
        return DiscoveryResult(port=candidates[0], candidates=candidates)
    return DiscoveryResult(port=None, candidates=candidates)
