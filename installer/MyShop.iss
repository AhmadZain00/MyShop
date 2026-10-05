#define MyAppName "MyShop"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "MyShop"
#define MyAppExeName "MyShop.exe"

[Setup]
AppId={{A4A8A4A1-2C0A-4D9A-8F31-4D9E8D1F1A01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\MyShop
DefaultGroupName=MyShop
OutputDir=dist-installer
OutputBaseFilename=MyShopSetup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\MyShop.exe
DisableProgramGroupPage=yes

[Files]
Source: "..\dist\MyShop.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\MyShop"; Filename: "{app}\MyShop.exe"
Name: "{group}\MyShop"; Filename: "{app}\MyShop.exe"

[Run]
Filename: "{app}\MyShop.exe"; Description: "تشغيل MyShop"; Flags: nowait postinstall skipifsilent
