@echo off
setlocal enabledelayedexpansion

title Debtinst_s - Zero-Dependency Fixed-Income Terminal
echo =================================================================
echo   Debtinst_s - Zero-Dependency Fixed-Income & Gold Bond Terminal
echo =================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 1. Check if compiled standalone executable exists
if exist "%SCRIPT_DIR%Debtinst_s.exe" (
    echo [*] Launching compiled standalone executable: Debtinst_s.exe...
    start "" "%SCRIPT_DIR%Debtinst_s.exe"
    exit /b 0
)

:: 2. Check if python / py is available and main.py exists
set "MAIN_PATH="
if exist "%SCRIPT_DIR%..\main.py" set "MAIN_PATH=%SCRIPT_DIR%..\main.py"
if exist "%SCRIPT_DIR%main.py" set "MAIN_PATH=%SCRIPT_DIR%main.py"

if defined MAIN_PATH (
    where py >nul 2>nul
    if !errorlevel! equ 0 (
        echo [*] Launching live local server via py launcher...
        start "" py "%MAIN_PATH%"
        exit /b 0
    )
    where python >nul 2>nul
    if !errorlevel! equ 0 (
        echo [*] Launching live local server via python...
        start "" python "%MAIN_PATH%"
        exit /b 0
    )
)

:: 3. Zero-Install Fallback: Launch standalone HTML in native chromeless desktop app mode
echo [*] No Python installation detected.
echo [*] Launching zero-install standalone HTML terminal in native desktop app mode...

set "HTML_FILE=%SCRIPT_DIR%Debtinst_s_Standalone.html"
if not exist "%HTML_FILE%" (
    echo [!] Error: Standalone HTML not found at %HTML_FILE%
    pause
    exit /b 1
)

:: Try Microsoft Edge app mode
where msedge >nul 2>nul
if %errorlevel% equ 0 (
    start "" msedge --app="file:///%HTML_FILE:\=/%"
    exit /b 0
)

:: Try Google Chrome app mode
where chrome >nul 2>nul
if %errorlevel% equ 0 (
    start "" chrome --app="file:///%HTML_FILE:\=/%"
    exit /b 0
)

:: Fallback to default browser
start "" "%HTML_FILE%"
exit /b 0
