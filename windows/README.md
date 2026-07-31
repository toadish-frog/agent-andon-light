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

## 3. Expect a SmartScreen warning — this is normal, not a build problem

Neither `andon-light.exe` nor `andon-light-setup.exe` is code-signed, so the first person to run either one will see Windows' "Windows protected your PC" SmartScreen prompt (unrecognized publisher), and some antivirus engines may flag the PyInstaller `--onefile` binary outright — PyInstaller onefile builds are commonly false-positived because the self-extract-to-temp-dir behavior at runtime resembles a malware dropper. Neither is specific to this build being broken.

- **To proceed past SmartScreen:** click "More info," then "Run anyway."
- **This is expected to affect real recipients**, not just test runs — pass along the click-through instructions with the installer, especially for non-technical recipients who'd otherwise assume it's actually dangerous and bail out.
- **Real fix, if this needs to look more legitimate later:** an Authenticode code-signing certificate (~$70–400/yr depending on vendor) removes the "Unknown Publisher" label; a brand-new cert still needs to build SmartScreen reputation over time unless it's EV. Not worth it for a handful of known recipients — revisit if distribution grows past that.

## 4. What to actually verify on real Windows hardware

This is the point of testing on your machine rather than guessing:

- **CDC driver:** confirmed (2026-07-31) — the RP2040-Zero enumerates as a COM port with zero extra steps, no `arduino-pico` INF needed.
- **PATH:** after installing, open a **new** terminal (PATH changes don't apply to already-open ones) and confirm `andon-light doctor` resolves and finds the device.
- **install-hooks from the finish page:** confirm the checkbox actually launches a visible console window with the interactive prompt, and that declining/confirming behaves as expected.
- **Uninstall:** confirm the Windows "Add or Remove Programs" entry cleanly removes the `PATH` entry and the installed files. (Inno Setup doesn't undo a `[Registry]` string append automatically — `andon-light.iss` has explicit `RemovePath`/`CurUninstallStepChanged` logic for this; verify it actually works, since a broken PATH edit on uninstall is bad enough to test carefully.)
