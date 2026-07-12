@echo off
echo === Building App Usage CLI Windows Executable ===

REM Check for virtual environment
SET PIP_CMD=pip
SET PYINSTALLER_CMD=pyinstaller

IF EXIST "..\env\Scripts\pip.exe" (
    SET PIP_CMD=..\env\Scripts\pip.exe
    SET PYINSTALLER_CMD=..\env\Scripts\pyinstaller.exe
)

REM 1. Install build tools if missing
%PIP_CMD% install pyinstaller

REM 2. Build single binary using PyInstaller
echo Running PyInstaller...
%PYINSTALLER_CMD% --onefile --name app-usage app_usage_cli\cli.py

REM 3. Package into a zip
echo Packaging to zip...
powershell Compress-Archive -Path dist\app-usage.exe -DestinationPath dist\app-usage_0.1.0_windows_amd64.zip -Force

echo === Done! ===
echo Executable is located in dist\app-usage.exe
echo Zip archive is located in dist\app-usage_0.1.0_windows_amd64.zip
