; Agent Andon Light — Windows installer (Inno Setup).
;
; Build andon-light.exe first (windows\build.ps1), then compile this with
; Inno Setup (iscc.exe windows\andon-light.iss, or open in the Inno Setup IDE
; and click Compile). Output lands in windows\dist\andon-light-setup.exe.
;
; Per-user install (no admin/UAC prompt) — the target audience for this
; installer is assumed non-technical, so it should ask for as little as
; possible: no elevation, one finish-page checkbox for hook setup, done.

#define MyAppName "Agent Andon Light"
#define MyAppVersion "0.1.0"
#define MyAppExeName "andon-light.exe"

[Setup]
AppId={{8F1B2C1A-6E4B-4B9E-9C2A-2F6C6A2B1A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Agent Andon Light
DefaultDirName={localappdata}\AndonLight
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ChangesEnvironment=yes
OutputBaseFilename=andon-light-setup
OutputDir=dist
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\andon-light.exe"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
; Prepend {app} to the current user's PATH if it isn't already there, so
; `andon-light` resolves by bare name — required for Claude Code hooks to
; call it, and for the user to use it from any terminal.
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app}"; Check: NeedsAddPath('{app}')

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

{ Inno Setup's [Registry] section doesn't know how to undo a string
  concatenation (ValueData: "{olddata};{app}") on uninstall — without this,
  the appended {app} entry is left in PATH forever after uninstalling. }
procedure RemovePath(Param: string);
var
  OrigPath, Padded: string;
  P: Integer;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
    exit;
  Padded := ';' + OrigPath + ';';
  P := Pos(';' + Param + ';', Padded);
  if P = 0 then
    exit;
  Delete(Padded, P, Length(Param) + 1);
  if (Length(Padded) > 0) and (Padded[1] = ';') then
    Delete(Padded, 1, 1);
  if (Length(Padded) > 0) and (Padded[Length(Padded)] = ';') then
    Delete(Padded, Length(Padded), 1);
  RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Padded);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RemovePath(ExpandConstant('{app}'));
end;

[Run]
; Same "show it, ask, then merge" flow as the CLI's interactive mode — the
; installer doesn't silently touch settings.json, it just launches the
; existing confirmation prompt in a console window. Unchecked by default:
; the user opts in on the finish page, they don't have to click through it.
Filename: "{cmd}"; Parameters: "/K ""{app}\{#MyAppExeName}"" install-hooks"; \
    Description: "Configure Claude Code hooks now (recommended)"; \
    Flags: postinstall nowait skipifsilent unchecked
