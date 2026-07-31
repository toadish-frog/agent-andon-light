# Windows installer — build & test

Everything here needs to actually run on Windows — build it there, not by cross-compiling from Linux.

## 1. Build the .exe

Prerequisites: Python 3.9+ on `PATH`.

```powershell
.\windows\build.ps1
```

This creates an isolated build venv at `windows\.build-venv` (doesn't touch any Python install you already have), builds `windows\dist\andon-light.exe` via PyInstaller, prints its size, and runs `andon-light.exe doctor` as a sanity check.

**Expected size:** low tens of MB. PyInstaller only bundles what it finds reachable from the entry point (`argparse` + `pyserial`, nothing exotic) — it doesn't "bundle everything" by default, so this was never realistically going to be hundreds of MB. If the printed size comes out much larger than expected, something unwanted got pulled in — worth checking `windows\build\andon-light\warn-andon-light.txt` (PyInstaller's own build log) for what.

## 2. Build the installer

Prerequisite: [Inno Setup](https://jrsoftware.org/isinfo.php) installed.

```powershell
iscc windows\andon-light.iss
```

(Or open `andon-light.iss` in the Inno Setup IDE and click Compile.) Output: `windows\dist\andon-light-setup.exe`.

The installer is per-user (no admin/UAC prompt), adds itself to the user's `PATH`, and offers a finish-page checkbox to run `andon-light.exe install-hooks` — same confirm-before-writing flow as the CLI's interactive mode, see `../hooks/README.md`.

## 3. What to actually verify on real Windows hardware

This is the point of testing on your machine rather than guessing:

- **CDC driver:** does the RP2040-Zero enumerate as a COM port with zero extra steps, or does Windows need the `arduino-pico` INF? `device/firmware/README.md` and `device/docs/TROUBLESHOOTING.md` currently hedge on this — once confirmed, update both with a definitive answer instead of a hedge.
- **PATH:** after installing, open a **new** terminal (PATH changes don't apply to already-open ones) and confirm `andon-light doctor` resolves and finds the device.
- **install-hooks from the finish page:** confirm the checkbox actually launches a visible console window with the interactive prompt, and that declining/confirming behaves as expected.
- **Uninstall:** confirm the Windows "Add or Remove Programs" entry cleanly removes the `PATH` entry and the installed files. (Inno Setup doesn't undo a `[Registry]` string append automatically — `andon-light.iss` has explicit `RemovePath`/`CurUninstallStepChanged` logic for this; verify it actually works, since a broken PATH edit on uninstall is bad enough to test carefully.)
