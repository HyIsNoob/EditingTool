; filepath: d:\fileluu\Tools\ProjectPic2Text\inno_setup.iss
; Inno Setup Script for KHyTool Application
; Basic configuration script for KHyTool

#define MyAppName "KHyTool"
#define MyAppVersion "1.1"
#define MyAppPublisher "Khang Hy"
#define MyAppURL "https://github.com/HyIsNoob"
#define MyAppExeName "KHyTool.exe"

; Determine the application source directory
#define SourcePath "dist\KHyTool"

[Setup]
; Application information
AppId={{EAE9CFA5-3B1C-4690-8E9F-B212DD11C140}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}

; Default installation directory
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}

; Disable asking to restart
AlwaysRestart=no

; Size information of the installation
; You should update these values according to the actual size
OutputDir=Output
OutputBaseFilename=KHyTool_Setup

; Compression settings
Compression=lzma
SolidCompression=yes

; Cosmetic settings
SetupIconFile=resources\icons\app_icon.ico
WizardStyle=modern

; Request privileges - needed for installing in Program Files
PrivilegesRequiredOverridesAllowed=dialog
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Include all files from the PyInstaller output
Source: "{#SourcePath}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Create start menu shortcuts
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
; Create desktop shortcut if selected
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Option to launch the application after installation completes
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent