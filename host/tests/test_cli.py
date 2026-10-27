"""Unit tests for andon_light.cli.

No test here opens a real serial port — SerialLink and port resolution are patched.
"""

from __future__ import annotations

import io
import unittest
from unittest import mock

from andon_light import cli


class BrightnessParsingTests(unittest.TestCase):
    def _parse(self, *argv: str):
        return cli.build_parser().parse_args(list(argv))

    def test_accepts_bounds(self):
        self.assertEqual(self._parse("brightness", "5").percent, 5)
        self.assertEqual(self._parse("brightness", "100").percent, 100)

    def test_rejects_out_of_range_and_non_integers(self):
        for value in ("4", "0", "101", "-10", "50.5", "abc", ""):
            with self.subTest(value=value), mock.patch("sys.stderr", new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as ctx:
                    self._parse("brightness", value)
                self.assertEqual(ctx.exception.code, 2)

    def test_requires_a_value(self):
        with mock.patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit):
                self._parse("brightness")


class BrightnessCommandTests(unittest.TestCase):
    def test_sends_brightness_command(self):
        link = mock.MagicMock()
        with mock.patch.object(cli, "_resolve_port", return_value="/dev/fake") as resolve, \
                mock.patch.object(cli, "SerialLink") as serial_link:
            serial_link.return_value.__enter__.return_value = link
            self.assertEqual(cli.main(["brightness", "30"]), 0)
        resolve.assert_called_once_with(None)
        serial_link.assert_called_once_with("/dev/fake")
        link.send.assert_called_once_with("B30")

    def test_explicit_port_is_passed_through(self):
        with mock.patch.object(cli, "_resolve_port", return_value="/dev/fake") as resolve, \
                mock.patch.object(cli, "SerialLink"):
            cli.main(["--port", "/dev/other", "brightness", "50"])
        resolve.assert_called_once_with("/dev/other")


if __name__ == "__main__":
    unittest.main()
