"""Thin wrapper around pyserial for sending Andon Light protocol commands."""

from __future__ import annotations

import time

import serial

BAUD_RATE = 115200

# Two hook-triggered `andon-light` invocations can occasionally land close enough
# together to contend for the port (e.g. overlapping hook events). Retry briefly
# on that specific transient case rather than dropping the color update.
_BUSY_RETRY_ATTEMPTS = 3
_BUSY_RETRY_DELAY_S = 0.15


class SerialLink:
    def __init__(self, port: str, baud: int = BAUD_RATE, timeout: float = 1.0):
        self._connection = self._open_with_retry(port, baud, timeout)

    @staticmethod
    def _open_with_retry(port: str, baud: int, timeout: float) -> serial.Serial:
        last_error: serial.SerialException | None = None
        for _ in range(_BUSY_RETRY_ATTEMPTS):
            try:
                return serial.Serial(port, baud, timeout=timeout)
            except serial.SerialException as exc:
                if "busy" not in str(exc).lower():
                    raise  # not transient contention — fail immediately
                last_error = exc
                time.sleep(_BUSY_RETRY_DELAY_S)
        assert last_error is not None
        raise last_error

    def send(self, command: str) -> None:
        self._connection.write(f"{command}\n".encode("ascii"))
        self._connection.flush()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SerialLink":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()
