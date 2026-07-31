# Builds a minimal andon-light.exe via PyInstaller. Run from PowerShell on
# Windows, from anywhere — paths below are resolved relative to this script:
#
#   .\windows\build.ps1
#
# Requires Python 3.9+ on PATH. Everything else (the build venv, PyInstaller)
# is created fresh in windows\.build-venv so this never touches any Python
# environment you already have.

$ErrorActionPreference = "Stop"

$WindowsDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $WindowsDir
$HostDir = Join-Path $RepoRoot "host"
$BuildVenv = Join-Path $WindowsDir ".build-venv"
$DistDir = Join-Path $WindowsDir "dist"
$WorkDir = Join-Path $WindowsDir "build"

Write-Host "Creating build venv at $BuildVenv"
python -m venv $BuildVenv
& "$BuildVenv\Scripts\pip.exe" install --quiet --upgrade pip
& "$BuildVenv\Scripts\pip.exe" install --quiet $HostDir pyinstaller

$SnippetSrc = Join-Path $HostDir "andon_light\data\settings.snippet.json"

# PyInstaller only bundles what its import-graph analysis actually finds
# reachable from andon_light_entry.py — it does not "bundle everything" by
# default, so a 400MB result was never really on the table for a CLI this
# small (just argparse + pyserial). The --exclude-module flags below are a
# light safety net against a couple of stdlib modules PyInstaller sometimes
# pulls in via indirect references even when unused (tkinter is the one
# that's actually sizeable, ~10MB, if it sneaks in). Expect a final size in
# the low tens of MB, dominated by the embedded Python interpreter itself.
& "$BuildVenv\Scripts\pyinstaller.exe" `
    --onefile `
    --name andon-light `
    --distpath $DistDir `
    --workpath $WorkDir `
    --specpath $WindowsDir `
    --add-data "$SnippetSrc;andon_light\data" `
    --exclude-module tkinter `
    --exclude-module unittest `
    --exclude-module test `
    --exclude-module distutils `
    --exclude-module lib2to3 `
    --exclude-module pydoc_data `
    (Join-Path $WindowsDir "andon_light_entry.py")

$Exe = Join-Path $DistDir "andon-light.exe"
$SizeMB = [math]::Round((Get-Item $Exe).Length / 1MB, 1)
Write-Host ""
Write-Host "Built $Exe ($SizeMB MB)"
Write-Host "Sanity check: $Exe doctor"
& $Exe doctor
