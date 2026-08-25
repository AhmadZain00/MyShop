@echo off
setlocal
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  echo Please create .venv and install requirements first.
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m PyInstaller --noconfirm --clean MyShop.spec
if errorlevel 1 exit /b 1
if not exist dist\MyShop\data mkdir dist\MyShop\data
if not exist dist\MyShop\portable.flag type nul > dist\MyShop\portable.flag

echo Build complete: dist\MyShop\MyShop.exe
