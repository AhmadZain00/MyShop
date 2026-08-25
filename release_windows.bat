@echo off
setlocal
title MyShop Production Release

echo ==========================================
echo MyShop - Production Windows Release Build
echo ==========================================

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found.
  exit /b 1
)

if not exist .venv\Scripts\python.exe python -m venv .venv
if errorlevel 1 exit /b 1

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

pip install -r requirements.txt
if errorlevel 1 exit /b 1

python scripts\validate_production.py
if errorlevel 1 exit /b 1

python -m pytest -q
if errorlevel 1 exit /b 1

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

python -m PyInstaller --clean --noconfirm MyShop.spec
if errorlevel 1 exit /b 1

echo.
echo EXE BUILD COMPLETE:
echo dist\MyShop\MyShop.exe
echo.

where ISCC.exe >nul 2>nul
if not errorlevel 1 (
    if exist installer\dist-installer rmdir /s /q installer\dist-installer
    ISCC.exe installer\MyShop.iss
    if errorlevel 1 exit /b 1
    echo INSTALLER BUILD COMPLETE:
    echo installer\dist-installer\MyShopSetup.exe
) else (
    echo ISCC.exe not found.
    echo EXE build succeeded; installer build was skipped.
)

echo.
echo RELEASE BUILD FINISHED.
endlocal
