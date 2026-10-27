"""Unit tests for andon_light.device_discovery.

list_ports.comports() is patched with fake ports, so these run without a device and
cover each OS's port naming (Linux /dev/ttyACM*, macOS /dev/cu.usbmodem*, Windows COM*).
"""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest import mock

from andon_light import device_discovery


def _port(device: str, vid: int | None):
    return SimpleNamespace(device=device, vid=vid)


def _discover(ports, env=None):
    with mock.patch.object(device_discovery.list_ports, "comports", return_value=ports), \
            mock.patch.dict(os.environ, env or {}, clear=False):
        if not env:
            os.environ.pop(device_discovery.ENV_PORT_OVERRIDE, None)
        return device_discovery.find_device_port()


class FindDevicePortTests(unittest.TestCase):
    def test_single_match_per_os_naming(self):
        for device in ("/dev/ttyACM0", "/dev/cu.usbmodem1101", "COM3"):
            with self.subTest(device=device):
                result = _discover([_port(device, device_discovery.DEFAULT_VID)])
                self.assertEqual(result.port, device)
                self.assertEqual(result.candidates, [device])

    def test_ignores_other_vendors_and_ports_without_vid(self):
        # macOS always lists built-in ports such as Bluetooth-Incoming-Port with no VID.
        ports = [
            _port("/dev/cu.Bluetooth-Incoming-Port", None),
            _port("/dev/cu.usbserial-0001", 0x0403),
            _port("/dev/cu.usbmodem1101", device_discovery.DEFAULT_VID),
        ]
        self.assertEqual(_discover(ports).port, "/dev/cu.usbmodem1101")

    def test_no_match(self):
        result = _discover([_port("/dev/cu.Bluetooth-Incoming-Port", None)])
        self.assertIsNone(result.port)
        self.assertEqual(result.candidates, [])

    def test_multiple_matches_are_not_auto_selected(self):
        ports = [
            _port("/dev/cu.usbmodem1101", device_discovery.DEFAULT_VID),
            _port("/dev/cu.usbmodem1201", device_discovery.DEFAULT_VID),
        ]
        result = _discover(ports)
        self.assertIsNone(result.port)
        self.assertEqual(result.candidates, ["/dev/cu.usbmodem1101", "/dev/cu.usbmodem1201"])

    def test_env_override_wins_without_scanning(self):
        with mock.patch.object(device_discovery.list_ports, "comports") as comports, \
                mock.patch.dict(os.environ, {device_discovery.ENV_PORT_OVERRIDE: "/dev/cu.custom"}):
            result = device_discovery.find_device_port()
        comports.assert_not_called()
        self.assertEqual(result.port, "/dev/cu.custom")


if __name__ == "__main__":
    unittest.main()
