"""Merges the Claude Code hooks snippet into settings.json, with explicit confirmation.

Never edits settings.json without an explicit yes from the caller — see
`../../hooks/README.md` and `../../device/docs/Implementation-Summary.md` Phase 7:
the hooks merge is required to be opt-in, not a silent install-time side effect.
"""

from __future__ import annotations

import json
import sys
from importlib import resources
from pathlib import Path
from typing import Callable

SNIPPET_RESOURCE = "data/settings.snippet.json"

GLOBAL_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
PROJECT_SETTINGS_PATH = Path(".claude") / "settings.json"


def load_snippet_hooks() -> dict:
    # PyInstaller onefile extracts bundled data next to sys._MEIPASS at
    # runtime; importlib.resources isn't guaranteed to resolve it there
    # across every PyInstaller version, so read it directly when frozen.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        text = (Path(sys._MEIPASS) / "andon_light" / SNIPPET_RESOURCE).read_text()
    else:
        text = resources.files("andon_light").joinpath(SNIPPET_RESOURCE).read_text()
    return json.loads(text)["hooks"]


def settings_path_for_scope(scope: str) -> Path:
    if scope == "global":
        return GLOBAL_SETTINGS_PATH
    if scope == "project":
        return PROJECT_SETTINGS_PATH
    raise ValueError(f"Unknown scope: {scope!r}")


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def merge_hooks(existing: dict, incoming_hooks: dict) -> tuple[dict, list[str]]:
    """Merge incoming_hooks into existing["hooks"], preserving every other key.

    Returns (merged settings, hook event names that already had a mapping and
    were overwritten) so the caller can warn before this happens.
    """
    merged = dict(existing)
    existing_hooks = dict(merged.get("hooks", {}))
    overwritten = [event for event in incoming_hooks if event in existing_hooks]
    existing_hooks.update(incoming_hooks)
    merged["hooks"] = existing_hooks
    return merged, overwritten


def write_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n")


def run(
    scope: str | None,
    assume_yes: bool,
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print,
) -> int:
    incoming_hooks = load_snippet_hooks()

    print_func("This will merge the following Claude Code hooks:\n")
    print_func(json.dumps({"hooks": incoming_hooks}, indent=2))
    print_func()

    if scope is None:
        if assume_yes:
            print_func("--yes requires --scope {global,project}.")
            return 1
        answer = input_func(
            "Scope — (g)lobal ~/.claude/settings.json or (p)roject ./.claude/settings.json? [g/p] "
        ).strip().lower()
        if answer.startswith("g"):
            scope = "global"
        elif answer.startswith("p"):
            scope = "project"
        else:
            print_func("Unrecognized scope, aborting. No changes made.")
            return 1

    path = settings_path_for_scope(scope)

    if not assume_yes:
        answer = input_func(f"Merge into {path}? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print_func("Aborted. No changes made.")
            return 1

    existing = load_settings(path)
    merged, overwritten = merge_hooks(existing, incoming_hooks)

    if overwritten and not assume_yes:
        print_func(
            f"Warning: this overwrites your existing hook mapping(s) for: {', '.join(overwritten)}"
        )
        answer = input_func("Continue and overwrite? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print_func("Aborted. No changes made.")
            return 1

    write_settings(path, merged)
    print_func(f"Hooks merged into {path}.")
    return 0
