@echo off
setlocal

echo === Building App Usage Windows Executables ===

REM --------------------------------------------------
REM Select Python interpreter
REM --------------------------------------------------
IF EXIST "..\env\Scripts\python.exe" (
    SET PYTHON=..\env\Scripts\python.exe
) ELSE (
    SET PYTHON=python
)

echo Using Python:
%PYTHON% --version

REM --------------------------------------------------
REM Install PyInstaller
REM --------------------------------------------------
echo.
echo Installing PyInstaller...
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install pyinstaller

IF ERRORLEVEL 1 (
    echo.
    echo ERROR: Failed to install PyInstaller.
    exit /b 1
)

REM --------------------------------------------------
REM Clean previous builds
REM --------------------------------------------------
IF EXIST build rmdir /s /q build
IF EXIST dist rmdir /s /q dist
IF EXIST app-usage.spec del /f /q app-usage.spec
IF EXIST app-usage-daemon.spec del /f /q app-usage-daemon.spec

REM --------------------------------------------------
REM Build CLI executable (console app)
REM --------------------------------------------------
echo.
echo Running PyInstaller (CLI)...

%PYTHON% -m PyInstaller ^
    --onefile ^
    --console ^
    --name app-usage ^
    app_usage_cli\cli.py

IF ERRORLEVEL 1 (
    echo.
    echo ERROR: CLI build failed.
    exit /b 1
)

REM --------------------------------------------------
REM Build daemon executable (no console window)
REM --------------------------------------------------
echo.
echo Running PyInstaller (daemon)...

%PYTHON% -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name app-usage-daemon ^
    app_usage_cli\cli.py

IF ERRORLEVEL 1 (
    echo.
    echo ERROR: Daemon build failed.
    exit /b 1
)

REM --------------------------------------------------
REM Create zip
REM --------------------------------------------------
echo.
echo Packaging executables...

powershell -Command ^
"Compress-Archive -Path 'dist\app-usage.exe','dist\app-usage-daemon.exe' -DestinationPath 'dist\app-usage_0.1.0_windows_amd64.zip' -Force"

IF ERRORLEVEL 1 (
    echo.
    echo WARNING: Zip creation failed.
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo Executables:
echo     dist\app-usage.exe            (CLI, has console window)
echo     dist\app-usage-daemon.exe     (daemon, no console window)
echo.
echo Zip:
echo     dist\app-usage_0.1.0_windows_amd64.zip

endlocal