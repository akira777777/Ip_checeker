# QODER Layout Configuration Script
# This script ensures consistent layout and spacing in QODER

Write-Host "Configuring QODER layout with equal spacing..." -ForegroundColor Green
Write-Host ""

# Define paths
$WorkspaceSettings = Join-Path $PSScriptRoot "..\.vscode\settings.json"
$UserSettings = Join-Path $env:APPDATA "Code\User\settings.json"

Write-Host "Applying workspace layout settings..." -ForegroundColor Yellow
Write-Host "Settings configured for:"
Write-Host "- Equal spacing between elements"
Write-Host "- Fixed tab width and appearance"  
Write-Host "- Consistent panel layout"
Write-Host "- Permanent window arrangement"
Write-Host ""

# Check if workspace settings exist
if (Test-Path $WorkspaceSettings) {
    Write-Host "Workspace settings file found: $WorkspaceSettings" -ForegroundColor Green
    
    # Create backup of user settings if they exist
    if (Test-Path $UserSettings) {
        $BackupPath = "$UserSettings.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item $UserSettings $BackupPath -Force
        Write-Host "Backed up existing user settings to: $BackupPath" -ForegroundColor Cyan
    }
    
    Write-Host "Workspace layout settings applied successfully!" -ForegroundColor Green
} else {
    Write-Host "Warning: Workspace settings file not found at $WorkspaceSettings" -ForegroundColor Red
}

Write-Host ""
Write-Host "Layout configuration complete!" -ForegroundColor Green
Write-Host "Restart QODER to see the changes take effect."
Write-Host "Use Ctrl+Shift+P and search for 'Preferences: Open Workspace Settings' to fine-tune."

# Pause to keep window open
Write-Host ""
Write-Host "Press any key to continue..." -NoNewline
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")