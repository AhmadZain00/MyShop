@echo off
setlocal
cd /d %~dp0
call build.bat
if errorlevel 1 exit /b 1
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
  echo Inno Setup 6 not found. Build the EXE first, then compile installer\MyShop.iss manually.
  exit /b 2
)
%ISCC% installer\MyShop.iss
if errorlevel 1 exit /b 1
echo Installer build complete: installer\dist-installer\MyShopSetup.exe
