"""Thin wrapper around pyserial for sending Andon Light protocol commands."""

from __future__ import annotations

import serial

BAUD_RATE = 115200


class SerialLink:
    def __init__(self, port: str, baud: int = BAUD_RATE, timeout: float = 1.0):
        self._connection = serial.Serial(port, baud, timeout=timeout)

    def send(self, command: str) -> None:
        self._connection.write(f"{command}\n".encode("ascii"))
        self._connection.flush()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SerialLink":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()
