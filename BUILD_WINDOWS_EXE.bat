@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher ^(py.exe^) not found.
  echo Install Python 3.10+ from python.org and rerun this file.
  pause
  exit /b 1
)

echo [1/5] Installing build dependencies...
py -3 -m pip install --upgrade pip pyinstaller hidapi
if errorlevel 1 goto :fail

echo [2/5] Building bridge EXE...
py -3 -m PyInstaller --noconfirm --clean --onefile --console --name APEX5_FH6_Bridge --hidden-import=hid bridge_worker.py
if errorlevel 1 goto :fail

echo [3/5] Building GUI EXE...
py -3 -m PyInstaller --noconfirm --clean --onefile --noconsole --name APEX5_FH6_GUI apex5_gui.pyw
if errorlevel 1 goto :fail

echo [4/5] Creating release folder...
if not exist profiles\soft.ini (echo ERROR: profiles\soft.ini missing & goto :fail)
if not exist profiles\medium.ini (echo ERROR: profiles\medium.ini missing & goto :fail)
if not exist profiles\hard.ini (echo ERROR: profiles\hard.ini missing & goto :fail)
if exist release rmdir /s /q release
mkdir release
copy /Y dist\APEX5_FH6_GUI.exe release\ >nul
copy /Y dist\APEX5_FH6_Bridge.exe release\ >nul
xcopy /E /I /Y profiles release\profiles >nul
copy /Y README.md release\ >nul
copy /Y START_APEX5_GUI.bat release\ >nul
copy /Y build_exe.bat release\ >nul 2>nul
copy /Y VERSION.txt release\ >nul

echo [5/5] Done.
echo.
echo Final files:
dir /b release
echo.
echo GUI:    release\APEX5_FH6_GUI.exe
echo Bridge: release\APEX5_FH6_Bridge.exe
echo.
pause
exit /b 0

:fail
echo.
echo BUILD FAILED.
pause
exit /b 1
