# Windows Installer: Build & Test

Everything here needs to run on Windows — build it there, not by cross-compiling from Linux.

## 1. Build the .exe

Prerequisites: Python 3.9+ on `PATH`.

```powershell
.\packaging\windows\build.ps1
```

Creates an isolated build venv at `packaging\windows\.build-venv` (doesn't touch any Python install you already have), builds `packaging\windows\dist\andon-light.exe` via PyInstaller, prints its size, and runs `andon-light.exe doctor` as a sanity check.

**Expected size:** low tens of MB — PyInstaller only bundles what's reachable from the entry point (`argparse` + `pyserial`, nothing exotic). If the size is much larger, check `packaging\windows\build\andon-light\warn-andon-light.txt` (PyInstaller's build log) for what got pulled in.

## 2. Build the Installer

Prerequisite: [Inno Setup](https://jrsoftware.org/isinfo.php).

```powershell
iscc packaging\windows\andon-light.iss
```

(Or open `andon-light.iss` in the Inno Setup IDE and click Compile.) Output: `packaging\windows\dist\andon-light-setup.exe`.

| Property | Behavior |
| --- | --- |
| Privilege | Per-user, no admin/UAC prompt |
| PATH | Adds itself to the user's `PATH` |
| Hooks | Finish-page checkbox runs `andon-light.exe install-hooks` — same confirm-before-writing flow as the CLI's interactive mode, see [`../../hooks/README.md`](../../hooks/README.md) |

## 3. SmartScreen Warning

Neither `andon-light.exe` nor `andon-light-setup.exe` is code-signed. Windows shows "Windows protected your PC" the first time either runs, and some antivirus engines may flag the PyInstaller `--onefile` binary outright — its self-extract-to-temp-dir behavior at runtime resembles a malware dropper. Neither means the build is broken.

| | |
| --- | --- |
| Fix | Click "More info," then "Run anyway." |
| Affects | Every recipient, not just test runs — pass along the click-through instructions with the installer. |
| Real fix, if ever needed | An Authenticode code-signing certificate (~$70–400/yr) removes the "Unknown Publisher" label; a new cert still needs to build SmartScreen reputation over time unless it's EV. Not worth it for a handful of known recipients. |

## 4. Verification Checklist

Test on real Windows hardware, not by inspection:

- [ ] **CDC driver** — RP2040-Zero enumerates as a COM port with zero extra steps, no `arduino-pico` INF needed.
- [ ] **PATH** — open a **new** terminal after installing (PATH changes don't apply to already-open ones) and confirm `andon-light doctor` resolves and finds the device.
- [ ] **install-hooks from the finish page** — checkbox launches a visible console window with the interactive prompt; declining/confirming both behave as expected.
- [ ] **Uninstall** — "Add or Remove Programs" cleanly removes both the `PATH` entry and the installed files. Inno Setup doesn't undo a `[Registry]` string append automatically — `andon-light.iss` has explicit `RemovePath`/`CurUninstallStepChanged` logic for this; verify it actually works.
