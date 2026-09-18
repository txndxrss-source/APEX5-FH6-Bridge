@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo APEX 5 FH6 Bridge - PUBLIC RELEASE BUILD
echo ==========================================
echo.

where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher ^(py.exe^) not found.
  echo Install Python 3.10+ for the BUILD MACHINE only.
  pause
  exit /b 1
)

py -3 -m pip install --upgrade pip pyinstaller hidapi
if errorlevel 1 goto :fail

py -3 -m PyInstaller --noconfirm --clean --onefile --console --name APEX5_FH6_Bridge --hidden-import=hid bridge_worker.py
if errorlevel 1 goto :fail

py -3 -m PyInstaller --noconfirm --clean --onefile --noconsole --name APEX5_FH6_GUI apex5_gui.pyw
if errorlevel 1 goto :fail

if exist release rmdir /s /q release
mkdir release
mkdir release\profiles

copy /Y dist\APEX5_FH6_GUI.exe release\ >nul
copy /Y dist\APEX5_FH6_Bridge.exe release\ >nul
copy /Y profiles\*.ini release\profiles\ >nul
copy /Y README.md release\ >nul
copy /Y VERSION.txt release\ >nul

echo.
echo Portable build created in release\
echo.
echo For the one-click installer, install Inno Setup 6 and run:
echo   ISCC.exe installer\APEX5_FH6_Bridge_Setup.iss
echo.
pause
exit /b 0

:fail
echo.
echo BUILD FAILED.
pause
exit /b 1
