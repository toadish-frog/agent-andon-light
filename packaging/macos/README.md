# macOS Install & Verify

No installer to build — like Linux, macOS is docs-only, installed straight from PyPI with `pipx`. No code signing or notarization involved, since nothing is distributed as a macOS binary.

**Status:** install path and unit tests confirmed on macOS 14.3 (Apple Silicon); device detection and serial writes not yet verified on real hardware — see [Verification Checklist](#4-verification-checklist).

## 1. Install

Pick the route that matches your setup. Both end with `andon-light` on your `PATH` in `~/.local/bin`.

### Route A: Homebrew

```txt
brew install pipx
pipx ensurepath
pipx install andon-light
```

If Homebrew no longer ships prebuilt packages for your macOS version, `brew install pipx` builds Python from source and can fail. Seen on macOS 14.3: `error "This compiler does not have support for efficient tail calling."` while building `python@3.15`. Use Route B instead — nothing is left installed by the failed attempt.

### Route B: macOS Built-In Python

Uses `/usr/bin/python3` from the Xcode Command Line Tools (`xcode-select --install` if it's missing). Python 3.9 or newer is enough.

```txt
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install andon-light
```

Open a **new** terminal afterwards — `ensurepath` only updates shells started after it runs.

### From a Repo Clone (Development)

```txt
cd host
python3 -m venv .venv
.venv/bin/pip install -e .
ln -s "$PWD/.venv/bin/andon-light" ~/.local/bin/andon-light
```

The symlink puts the editable install on `PATH` so agent hooks can call it. It follows whichever branch is checked out.

## 2. Verify

```txt
andon-light doctor
```

Expect `Found device on /dev/cu.usbmodem…`. No group membership or driver is needed — macOS gives the logged-in user access to USB serial ports by default. If it reports `No device found`, see [`../../device/docs/TROUBLESHOOTING.md`](../../device/docs/TROUBLESHOOTING.md) macOS-Specific section.

## 3. Wire Up Hooks

```txt
andon-light install-hooks                 # Claude Code (default)
andon-light install-hooks --agent codex   # Codex CLI
```

Prints the exact `hooks` block before touching anything, asks for confirmation, and lets you pick global vs. project scope — see [`../../hooks/claude/README.md`](../../hooks/claude/README.md) (Claude Code) or [`../../hooks/codex/README.md`](../../hooks/codex/README.md) (Codex CLI).

Hooks call `andon-light` by bare name, so the agent must see `~/.local/bin` on its `PATH`. An agent started from a terminal inherits it. An agent started as a GUI app (Dock, Spotlight) gets launchd's minimal `PATH` instead, and every hook fails silently because of `|| true` — start it from a terminal, or edit the hook commands to the full path from `which andon-light`.

## 4. Verification Checklist

Test on a real Mac with a real unit, not by inspection:

- [ ] **Detection** — `andon-light doctor` reports exactly one `/dev/cu.usbmodem…` port, with no `--port` needed.
- [ ] **Writes** — `andon-light set working|waiting|idle|compacting` each change the light; `scripts/dummy_workflow_test.sh` runs through every state.
- [ ] **No reset on open** — each command changes color directly, with no blank or flicker first (macOS asserts DTR when the port opens).
- [ ] **Busy port** — with Arduino IDE's Serial Monitor open, `andon-light set idle` either succeeds or fails with a one-line `serial error … Resource busy` message and exit code 1, never a traceback. (macOS only refuses a second open if the first process locked the port exclusively; record which behavior you see.)
- [ ] **Hooks end to end** — after `install-hooks` and a new Claude Code session, the light follows prompts, tool calls, permission requests and session end.
- [ ] **Unplug/replug** — the port name may change; `doctor` still finds it without reconfiguring.
