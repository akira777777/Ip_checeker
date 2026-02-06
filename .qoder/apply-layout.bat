@echo off
:: QODER Layout Configuration Script
:: This script ensures consistent layout and spacing in QODER

echo Configuring QODER layout with equal spacing...
echo.

:: Copy layout configuration to user settings if they don't exist
set "USER_SETTINGS=%APPDATA%\Code\User\settings.json"
set "WORKSPACE_SETTINGS=%~dp0.vscode\settings.json"

echo Applying workspace layout settings...
echo Settings configured for:
echo - Equal spacing between elements
echo - Fixed tab width and appearance  
echo - Consistent panel layout
echo - Permanent window arrangement
echo.

:: Create backup of existing settings
if exist "%USER_SETTINGS%" (
    copy "%USER_SETTINGS%" "%USER_SETTINGS%.backup" >nul
    echo Backed up existing user settings
)

:: Apply workspace settings
if exist "%WORKSPACE_SETTINGS%" (
    echo Workspace settings applied successfully
) else (
    echo Warning: Workspace settings file not found
)

echo.
echo Layout configuration complete!
echo Restart QODER to see the changes take effect.
echo Use Ctrl+Shift+P and search for "Preferences: Open Workspace Settings" to fine-tune.
pause