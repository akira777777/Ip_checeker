# VSCode PowerShell Profile for Administrative Work
# This profile loads administrative functions and settings when PowerShell starts in VSCode

Write-Host "Loading VSCode Administrative PowerShell Profile..." -ForegroundColor Green

# Check if running with elevated privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "Running with Administrative privileges" -ForegroundColor Cyan
    $host.UI.RawUI.BackgroundColor = 'DarkBlue'
    $host.PrivateData.ErrorForegroundColor = 'Red'
    $host.PrivateData.ErrorBackgroundColor = 'Black'
} else {
    Write-Host "Running without Administrative privileges - some features may be limited" -ForegroundColor Yellow
}

# Load administrative automation functions
$adminFunctionsPath = Join-Path $PSScriptRoot "admin-automation-functions.ps1"
if (Test-Path $adminFunctionsPath) {
    Import-Module $adminFunctionsPath -Force
    Write-Host "Administrative automation functions loaded" -ForegroundColor Green
}

# Set execution policy for current session (only affects this session)
try {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
    Write-Host "Execution policy set for current session" -ForegroundColor Green
}
catch {
    Write-Host "Could not set execution policy: $_" -ForegroundColor Red
}

# Define useful aliases for administrative tasks
Set-Alias -Name vscadmin -Value code
Set-Alias -Name vscconf -Value "d:\Ip_checeker\.qoder\.vscode\settings.json"
Set-Alias -Name vscws -Value "d:\Ip_checeker\.qoder\workspace-layout.code-workspace"

# Add useful functions to the profile
function Show-AdminStatus {
    <#
    .SYNOPSIS
        Shows the current administrative status and loaded modules
    .DESCRIPTION
        Displays whether the session is running with administrative privileges and which admin modules are loaded
    #>
    Write-Host "VSCode Administrative Session Status" -ForegroundColor Cyan
    Write-Host "====================================" -ForegroundColor White
    Write-Host "Admin Privileges: $(([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))" -ForegroundColor $($isAdmin ? "Green" : "Yellow")
    Write-Host "Profile Path: $PROFILE" -ForegroundColor Gray
    Write-Host "Loaded Modules:" -ForegroundColor Gray
    Get-Module | Where-Object {$_.Name -like "*admin*" -or $_.Name -like "*vscode*"} | ForEach-Object { Write-Host "  - $($_.Name) v$($_.Version)" -ForegroundColor Gray }
    Write-Host ""
    Write-Host "Available Admin Functions:" -ForegroundColor Gray
    Get-Command -Module (Get-Module | Where-Object {$_.Name -like "*admin*" -or $_.Name -like "*vscode*"}) | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Gray }
}

function Start-VSCodeAsAdmin {
    <#
    .SYNOPSIS
        Starts VSCode with administrative privileges
    .DESCRIPTION
        Launches a new VSCode instance with administrative privileges
    #>
    try {
        $codePath = Get-Command code -ErrorAction Stop
        Start-Process -FilePath $codePath.Source -Verb RunAs -ArgumentList "--folder-uri", "file:///$((Get-Location).Path)"
        Write-Host "VSCode started with administrative privileges" -ForegroundColor Green
    }
    catch {
        Write-Host "Could not start VSCode as admin: $_" -ForegroundColor Red
    }
}

function Get-AdminVSCodeSettings {
    <#
    .SYNOPSIS
        Retrieves the current VSCode administrative settings
    .DESCRIPTION
        Shows the current VSCode settings that affect administrative work
    #>
    $settingsPath = "d:\Ip_checeker\.qoder\.vscode\settings.json"
    if (Test-Path $settingsPath) {
        $settings = Get-Content $settingsPath | ConvertFrom-Json
        Write-Host "VSCode Administrative Settings Loaded:" -ForegroundColor Cyan
        Write-Host "  - Auto Update Extensions: $($settings.'extensions.autoUpdate')" -ForegroundColor Gray
        Write-Host "  - Telemetry Level: $($settings.'telemetry.telemetryLevel')" -ForegroundColor Gray
        Write-Host "  - Trusted Workspace: $($settings.'security.workspace.trust.untrustedFiles')" -ForegroundColor Gray
        Write-Host "  - Terminal Shell: $($settings.'terminal.integrated.shell.windows')" -ForegroundColor Gray
        Write-Host "  - Auto Format on Save: $($settings.'editor.formatOnSave')" -ForegroundColor Gray
    } else {
        Write-Host "VSCode settings file not found at: $settingsPath" -ForegroundColor Red
    }
}

function Test-AdminCapabilities {
    <#
    .SYNOPSIS
        Tests administrative capabilities
    .DESCRIPTION
        Runs a series of tests to verify administrative capabilities are available
    #>
    Write-Host "Testing Administrative Capabilities..." -ForegroundColor Cyan

    # Test registry access
    try {
        $testRegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
        $testValue = Get-ItemProperty -Path $testRegPath -ErrorAction Stop
        Write-Host "✓ Registry access: Available" -ForegroundColor Green
    } catch {
        Write-Host "✗ Registry access: Limited" -ForegroundColor Red
    }

    # Test file system access
    try {
        $testPath = "$env:SystemRoot\TestAdminAccess.tmp"
        "" | Out-File -FilePath $testPath -ErrorAction Stop
        Remove-Item -Path $testPath -ErrorAction Stop
        Write-Host "✓ File system access: Available" -ForegroundColor Green
    } catch {
        Write-Host "✗ File system access: Limited" -ForegroundColor Red
    }

    # Test service access
    try {
        Get-Service -Name WinRM -ErrorAction Stop | Out-Null
        Write-Host "✓ Service access: Available" -ForegroundColor Green
    } catch {
        Write-Host "✗ Service access: Limited" -ForegroundColor Red
    }

    # Test network adapter configuration
    try {
        Get-NetIPConfiguration -ErrorAction Stop | Out-Null
        Write-Host "✓ Network configuration access: Available" -ForegroundColor Green
    } catch {
        Write-Host "✗ Network configuration access: Limited" -ForegroundColor Red
    }

    Write-Host "Administrative capability test complete." -ForegroundColor Cyan
}

# Auto-run status check
Show-AdminStatus

# Welcome message
Write-Host ""
Write-Host "VSCode Administrative PowerShell Environment Ready" -ForegroundColor Green
Write-Host "Type 'Show-AdminStatus' for status, or 'Get-Help function-name' for help on admin functions" -ForegroundColor Yellow
Write-Host ""
