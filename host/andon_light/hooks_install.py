"""Merges an agent's hooks snippet into its config file, with explicit confirmation.

Never edits a config file without an explicit yes from the caller — see
`../../hooks/claude/README.md` / `../../hooks/codex/README.md` and
`../../device/docs/Implementation-Summary.md` Phase 7: the hooks merge is
required to be opt-in, not a silent install-time side effect.
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

CODEX_SNIPPET_RESOURCE = "data/codex.hooks.json"

CODEX_GLOBAL_HOOKS_PATH = Path.home() / ".codex" / "hooks.json"
CODEX_PROJECT_HOOKS_PATH = Path(".codex") / "hooks.json"

# Per-agent display label and post-merge note. Paths and the snippet resource
# stay as their own module-level constants (above) rather than living in this
# dict, so tests can keep patching them individually by name.
AGENT_LABELS = {
    "claude": "Claude Code",
    "codex": "Codex CLI",
}

# Codex requires an explicit trust step in-CLI before a new/changed hooks.json
# actually runs — there's no way to pre-trust it from outside the CLI, so
# install-hooks has to say so or the hooks will silently no-op.
AGENT_POST_INSTALL_NOTES = {
    "codex": (
        "Codex won't run these hooks until you trust them — start Codex CLI, "
        "run /hooks, and confirm the new/changed definitions."
    ),
}


def load_snippet_hooks(agent: str = "claude") -> dict:
    resource = SNIPPET_RESOURCE if agent == "claude" else CODEX_SNIPPET_RESOURCE
    # PyInstaller onefile extracts bundled data next to sys._MEIPASS at
    # runtime; importlib.resources isn't guaranteed to resolve it there
    # across every PyInstaller version, so read it directly when frozen.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        text = (Path(sys._MEIPASS) / "andon_light" / resource).read_text()
    else:
        text = resources.files("andon_light").joinpath(resource).read_text()
    return json.loads(text)["hooks"]


def settings_path_for_scope(scope: str, agent: str = "claude") -> Path:
    if agent == "claude":
        if scope == "global":
            return GLOBAL_SETTINGS_PATH
        if scope == "project":
            return PROJECT_SETTINGS_PATH
    elif agent == "codex":
        if scope == "global":
            return CODEX_GLOBAL_HOOKS_PATH
        if scope == "project":
            return CODEX_PROJECT_HOOKS_PATH
    else:
        raise ValueError(f"Unknown agent: {agent!r}")
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
    agent: str = "claude",
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print,
) -> int:
    label = AGENT_LABELS[agent]
    incoming_hooks = load_snippet_hooks(agent)

    print_func(f"This will merge the following {label} hooks:\n")
    print_func(json.dumps({"hooks": incoming_hooks}, indent=2))
    print_func()

    if scope is None:
        if assume_yes:
            print_func("--yes requires --scope {global,project}.")
            return 1
        global_path = settings_path_for_scope("global", agent)
        project_path = settings_path_for_scope("project", agent)
        answer = input_func(
            f"Scope — (g)lobal {global_path} or (p)roject {project_path}? [g/p] "
        ).strip().lower()
        if answer.startswith("g"):
            scope = "global"
        elif answer.startswith("p"):
            scope = "project"
        else:
            print_func("Unrecognized scope, aborting. No changes made.")
            return 1

    path = settings_path_for_scope(scope, agent)

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
    note = AGENT_POST_INSTALL_NOTES.get(agent)
    if note:
        print_func(note)
    return 0
