; VoxWave Installer — Inno Setup Script
; Compile avec : iscc installers\voxwave.iss
; Necessite : Inno Setup 6+ (https://jrsoftware.org/isdown.php)

#define MyAppName "VoxWave"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "VoxWave"
#define MyAppURL "https://voxwave.app"
#define MyAppExeName "VoxWave.exe"

[Setup]
; Identifiant unique de l'app (ne JAMAIS changer apres publication)
AppId={{B7E3F4A1-2C5D-4E8F-9A1B-3D6E7F8C9D0E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Pas besoin de droits admin (install dans AppData par defaut)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=VoxWave-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Taille estimee en KB
ExtraDiskSpaceRequired=0
UninstallDisplayIcon={app}\{#MyAppExeName}
; Empecher les installations multiples
AppMutex=VoxWaveMutex

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Lancer VoxWave au demarrage de Windows"; GroupDescription: "Options:"

[Files]
; Dossier onedir complet (exe + DLLs/SO — obligation LGPL pour PySide6/pynput)
Source: "..\dist\VoxWave\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Menu Demarrer
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstaller {#MyAppName}"; Filename: "{uninstallexe}"
; Bureau (optionnel)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
; Demarrage automatique (optionnel)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
; Lancer apres installation
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Nettoyer les fichiers de config utilisateur a la desinstallation
Type: filesandordirs; Name: "{localappdata}\VoxWave"

[Code]
// Fermer VoxWave avant installation/mise a jour
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  // Tenter de fermer VoxWave si en cours d'execution
  Exec('taskkill', '/f /im VoxWave.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function FileExists(FileName: string): Boolean;
begin
  Result := FileOrDirExists(FileName);
end;
