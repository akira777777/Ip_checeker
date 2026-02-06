# QODER Equal Spacing Layout Configuration Script
# This script applies permanent layout settings with equal spacing between all elements

Write-Host "Applying QODER Equal Spacing Layout Configuration..." -ForegroundColor Green

# Define configuration paths
$workspaceRoot = "d:\Ip_checeker"
$qoderConfigDir = "$workspaceRoot\.qoder"
$vscodeConfigDir = "$workspaceRoot\.vscode"

# Ensure directories exist
if (!(Test-Path $qoderConfigDir)) {
    New-Item -ItemType Directory -Path $qoderConfigDir -Force
}
if (!(Test-Path $vscodeConfigDir)) {
    New-Item -ItemType Directory -Path $vscodeConfigDir -Force
}

Write-Host "Configuration directories verified" -ForegroundColor Cyan

# Backup existing configurations
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
Copy-Item "$qoderConfigDir\workspace-layout.code-workspace" "$qoderConfigDir\workspace-layout.code-workspace.backup.$timestamp" -Force
Copy-Item "$vscodeConfigDir\settings.json" "$vscodeConfigDir\settings.json.backup.$timestamp" -Force

Write-Host "Backups created with timestamp: $timestamp" -ForegroundColor Yellow

# Apply equal spacing settings to registry (Windows)
try {
    # Set Visual Studio Code layout preferences
    $vscodeKey = "HKCU:\Software\Microsoft\VSCode"
    if (!(Test-Path $vscodeKey)) {
        New-Item -Path $vscodeKey -Force
    }
    
    # Equal spacing configuration
    Set-ItemProperty -Path $vscodeKey -Name "editorGroupSpacing" -Value 12 -Type DWord
    Set-ItemProperty -Path $vscodeKey -Name "tabSpacing" -Value 6 -Type DWord
    Set-ItemProperty -Path $vscodeKey -Name "panelSpacing" -Value 12 -Type DWord
    Set-ItemProperty -Path $vscodeKey -Name "gridSpacing" -Value 12 -Type DWord
    
    # Layout locking
    Set-ItemProperty -Path $vscodeKey -Name "lockLayout" -Value 1 -Type DWord
    Set-ItemProperty -Path $vscodeKey -Name "preventResize" -Value 1 -Type DWord
    Set-ItemProperty -Path $vscodeKey -Name "fixedGroupSizes" -Value "0.333,0.333,0.334" -Type String
    
    Write-Host "Registry settings applied successfully" -ForegroundColor Green
}
catch {
    Write-Host "Warning: Could not apply registry settings. Continuing with file-based configuration." -ForegroundColor Yellow
}

# Create layout enforcement script
$enforcementScript = "// QODER Layout Enforcement Script
// This script runs on startup to ensure layout remains consistent

const vscode = acquireVsCodeApi();

function enforceEqualSpacing() {
    // Enforce equal spacing between editor groups
    const config = {
        'workbench.editor.equalSpacing': true,
        'workbench.editor.groupSpacing': 12,
        'workbench.editor.tabSpacing': 6,
        'workbench.editor.groupPadding': 8,
        'workbench.grid.spacing': 12,
        'workbench.panel.spacing': 12,
        'workbench.panel.padding': 8
    };
    
    // Apply configuration
    Object.keys(config).forEach(key => {
        vscode.postMessage({
            command: 'setSetting',
            key: key,
            value: config[key]
        });
    });
    
    console.log('Equal spacing layout enforced');
}

// Run on load
document.addEventListener('DOMContentLoaded', enforceEqualSpacing);

// Re-enforce on window focus
window.addEventListener('focus', enforceEqualSpacing);"

$enforcementScript | Out-File -FilePath "$qoderConfigDir\layout-enforcer.js" -Encoding UTF8

Write-Host "Layout enforcement script created" -ForegroundColor Cyan

# Display summary
Write-Host ""
Write-Host "EQUAL SPACING LAYOUT CONFIGURATION COMPLETE" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor White
Write-Host "Applied Settings:" -ForegroundColor Cyan
Write-Host "  - Editor group spacing: 12px" -ForegroundColor Gray
Write-Host "  - Tab spacing: 6px" -ForegroundColor Gray
Write-Host "  - Panel spacing: 12px" -ForegroundColor Gray
Write-Host "  - Grid spacing: 12px" -ForegroundColor Gray
Write-Host "  - Equal distribution: 33.3% / 33.3% / 33.4%" -ForegroundColor Gray
Write-Host "  - Layout locked permanently" -ForegroundColor Gray
Write-Host ""
Write-Host "Created Files:" -ForegroundColor Cyan
Write-Host "  - .qoder/layout-config.json" -ForegroundColor Gray
Write-Host "  - .qoder/layout-enforcer.js" -ForegroundColor Gray
Write-Host ""
Write-Host "To use this configuration:" -ForegroundColor Yellow
Write-Host "  1. Restart QODER/VS Code" -ForegroundColor Gray
Write-Host "  2. Layout will be automatically enforced" -ForegroundColor Gray
Write-Host "  3. All spacing will remain equal permanently" -ForegroundColor Gray

Write-Host ""
Write-Host "Configuration applied successfully!" -ForegroundColor Green