"""Command-line entry point for the andon-light host driver."""

from __future__ import annotations

import argparse
import sys

import serial

from .device_discovery import find_device_port
from .hooks_install import run as run_install_hooks
from .serial_link import SerialLink

COLOR_COMMANDS = {
    "working": "G",
    "waiting": "Y",
    "idle": "R",
    "compacting": "C",
}


def _resolve_port(explicit_port: str | None) -> str:
    if explicit_port:
        return explicit_port

    result = find_device_port()
    if result.port:
        return result.port
    if result.candidates:
        raise SystemExit(
            f"Multiple possible devices found: {result.candidates}. "
            "Pick one with --port or set ANDON_LIGHT_PORT."
        )
    raise SystemExit("No Andon Light device found. Plug it in, or pass --port explicitly.")


def cmd_set(args: argparse.Namespace) -> None:
    port = _resolve_port(args.port)
    with SerialLink(port) as link:
        link.send(COLOR_COMMANDS[args.state])


def cmd_heartbeat(args: argparse.Namespace) -> None:
    port = _resolve_port(args.port)
    with SerialLink(port) as link:
        link.send("H")


def cmd_doctor(_args: argparse.Namespace) -> None:
    result = find_device_port()
    if result.port:
        print(f"Found device on {result.port}")
    elif result.candidates:
        print(f"Multiple candidates, none auto-selected: {result.candidates}")
    else:
        print("No device found.")


def cmd_install_hooks(args: argparse.Namespace) -> int:
    return run_install_hooks(scope=args.scope, assume_yes=args.yes)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="andon-light")
    parser.add_argument("--port", help="Explicit serial port, overrides auto-detection")
    subparsers = parser.add_subparsers(required=True)

    set_parser = subparsers.add_parser("set", help="Set the light's state")
    set_parser.add_argument("state", choices=COLOR_COMMANDS.keys())
    set_parser.set_defaults(func=cmd_set)

    heartbeat_parser = subparsers.add_parser(
        "heartbeat", help="Send a keepalive without changing color"
    )
    heartbeat_parser.set_defaults(func=cmd_heartbeat)

    doctor_parser = subparsers.add_parser(
        "doctor", help="Detect the device and report its port"
    )
    doctor_parser.set_defaults(func=cmd_doctor)

    install_hooks_parser = subparsers.add_parser(
        "install-hooks", help="Merge the Claude Code hooks into settings.json"
    )
    install_hooks_parser.add_argument(
        "--scope",
        choices=["global", "project"],
        default=None,
        help="global (~/.claude/settings.json) or project (./.claude/settings.json)",
    )
    install_hooks_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompts (requires --scope)",
    )
    install_hooks_parser.set_defaults(func=cmd_install_hooks)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except serial.SerialException as exc:
        print(f"andon-light: serial error: {exc}", file=sys.stderr)
        return 1
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
