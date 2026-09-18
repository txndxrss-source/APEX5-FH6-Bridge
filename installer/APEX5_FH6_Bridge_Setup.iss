#define MyAppName "APEX 5 · FH6 Adaptive Trigger Bridge"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "APEX5 FH6 Bridge"
#define MyAppExeName "APEX5_FH6_GUI.exe"

[Setup]
AppId={{6D3E9E88-B9C9-4B8F-9F1E-APEX5FH6BRIDGE2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\APEX5FH6Bridge
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=.
OutputBaseFilename=APEX5_FH6_Bridge_Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes

[Files]
Source: "..\release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\APEX 5 FH6 Bridge"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\APEX 5 FH6 Bridge"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\README"; Filename: "{app}\README.md"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch APEX 5 FH6 Bridge"; Flags: nowait postinstall skipifsilent
