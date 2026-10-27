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

# Must match LedController::kMinBrightnessPercent / kMaxBrightnessPercent in firmware —
# below 5% the status pixel rounds to off.
MIN_BRIGHTNESS_PERCENT = 5
MAX_BRIGHTNESS_PERCENT = 100


def _brightness_percent(value: str) -> int:
    try:
        percent = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid percent: {value!r} (expected a whole number)")
    if not MIN_BRIGHTNESS_PERCENT <= percent <= MAX_BRIGHTNESS_PERCENT:
        raise argparse.ArgumentTypeError(
            f"percent must be between {MIN_BRIGHTNESS_PERCENT} and {MAX_BRIGHTNESS_PERCENT}, got {percent}"
        )
    return percent


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


def cmd_brightness(args: argparse.Namespace) -> None:
    port = _resolve_port(args.port)
    with SerialLink(port) as link:
        link.send(f"B{args.percent}")


def cmd_doctor(_args: argparse.Namespace) -> None:
    result = find_device_port()
    if result.port:
        print(f"Found device on {result.port}")
    elif result.candidates:
        print(f"Multiple candidates, none auto-selected: {result.candidates}")
    else:
        print("No device found.")


def cmd_install_hooks(args: argparse.Namespace) -> int:
    return run_install_hooks(scope=args.scope, assume_yes=args.yes, agent=args.agent)


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

    brightness_parser = subparsers.add_parser(
        "brightness", help="Set LED brightness as a percent of maximum (saved on the device)"
    )
    brightness_parser.add_argument(
        "percent",
        type=_brightness_percent,
        help=f"{MIN_BRIGHTNESS_PERCENT}-{MAX_BRIGHTNESS_PERCENT}",
    )
    brightness_parser.set_defaults(func=cmd_brightness)

    doctor_parser = subparsers.add_parser(
        "doctor", help="Detect the device and report its port"
    )
    doctor_parser.set_defaults(func=cmd_doctor)

    install_hooks_parser = subparsers.add_parser(
        "install-hooks", help="Merge agent hooks into the target agent's config"
    )
    install_hooks_parser.add_argument(
        "--agent",
        choices=["claude", "codex"],
        default="claude",
        help="Which agent's hooks to install (default: claude)",
    )
    install_hooks_parser.add_argument(
        "--scope",
        choices=["global", "project"],
        default=None,
        help=(
            "global or project config scope — for claude: ~/.claude/settings.json "
            "or ./.claude/settings.json; for codex: ~/.codex/hooks.json or ./.codex/hooks.json"
        ),
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
