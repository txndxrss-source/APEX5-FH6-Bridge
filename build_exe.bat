@echo off
setlocal
cd /d "%~dp0"

py -m pip install pyinstaller hidapi
if errorlevel 1 (
    echo Failed to install build dependencies.
    pause
    exit /b 1
)

pyinstaller --noconfirm --clean --onedir --console --name APEX5_FH6_Bridge --hidden-import=hid bridge_worker.py
if errorlevel 1 (
    echo Bridge build failed.
    pause
    exit /b 1
)

pyinstaller --noconfirm --clean --onedir --noconsole --name APEX5_FH6_GUI apex5_gui.pyw
if errorlevel 1 (
    echo GUI build failed.
    pause
    exit /b 1
)

xcopy /E /I /Y profiles dist\APEX5_FH6_GUI\profiles >nul
copy /Y dist\APEX5_FH6_Bridge\APEX5_FH6_Bridge.exe dist\APEX5_FH6_GUI\ >nul
copy /Y profiles\*.ini dist\APEX5_FH6_GUI\ >nul 2>nul
copy /Y README.md dist\APEX5_FH6_GUI\ >nul
copy /Y START_APEX5_GUI.bat dist\APEX5_FH6_GUI\ >nul

copy /Y dist\APEX5_FH6_GUI\APEX5_FH6_GUI.exe . >nul
copy /Y dist\APEX5_FH6_GUI\APEX5_FH6_Bridge.exe . >nul

echo.
echo ===============================================
echo Build complete.
echo Launcher: START_APEX5_GUI.bat
echo EXE:      APEX5_FH6_GUI.exe
echo ===============================================
endlocal
pause
