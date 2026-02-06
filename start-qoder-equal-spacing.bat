@echo off
echo Starting QODER with equal spacing layout...
cd /d "d:\Ip_checeker"

REM Apply layout configuration
powershell -ExecutionPolicy Bypass -File ".qoder\configure-equal-spacing.ps1"

REM Start QODER/VS Code
code .

echo QODER started with permanent equal spacing configuration
pause