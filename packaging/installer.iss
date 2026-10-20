#ifndef PayloadDirectory
  #error PayloadDirectory must be provided
#endif
#ifndef OutputDirectory
  #error OutputDirectory must be provided
#endif

[Setup]
AppId={{14561C28-9239-463F-A9C4-9E032A122419}
AppName=murums PS4 PKG Extractor UI
AppVersion=0.1.0
AppPublisher=murums
DefaultDirName={localappdata}\Programs\murums PS4 PKG Extractor UI
DefaultGroupName=murums PS4 PKG Extractor UI
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.18362
OutputDir={#OutputDirectory}
OutputBaseFilename=ps4-pkg-extractor-ui-0.1.0-windows-x64-setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\PS4 PKG Extractor UI.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "{#PayloadDirectory}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PS4 PKG Extractor UI"; Filename: "{app}\PS4 PKG Extractor UI.exe"
Name: "{autodesktop}\PS4 PKG Extractor UI"; Filename: "{app}\PS4 PKG Extractor UI.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PS4 PKG Extractor UI.exe"; Description: "Open PS4 PKG Extractor UI"; Flags: nowait postinstall skipifsilent
