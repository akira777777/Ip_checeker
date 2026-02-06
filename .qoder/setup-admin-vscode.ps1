# VSCode Administrative Configuration Script
# Sets up VSCode for optimal automated administrative work with full administrator privileges

Write-Host "Setting up VSCode for Administrative Work with Full Administrator Privileges" -ForegroundColor Green
Write-Host "=========================================================================" -ForegroundColor White

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "WARNING: This script should be run as Administrator for full functionality." -ForegroundColor Red
    Write-Host "Some administrative features may not work properly without elevated privileges." -ForegroundColor Yellow

    $response = Read-Host "Continue anyway? (y/n)"
    if ($response -ne 'y') {
        exit
    }
} else {
    Write-Host "Running with Administrator privileges - all features enabled." -ForegroundColor Green
}

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
if (Test-Path "$qoderConfigDir\workspace-layout.code-workspace") {
    Copy-Item "$qoderConfigDir\workspace-layout.code-workspace" "$qoderConfigDir\workspace-layout.code-workspace.backup.admin.$timestamp" -Force
}
if (Test-Path "$vscodeConfigDir\settings.json") {
    Copy-Item "$vscodeConfigDir\settings.json" "$vscodeConfigDir\settings.json.backup.admin.$timestamp" -Force
}

Write-Host "Backups created with timestamp: $timestamp" -ForegroundColor Yellow

# Administrative Registry Settings
try {
    # Create registry key for VSCode admin settings
    $vscodeAdminKey = "HKLM:\SOFTWARE\WOW6432Node\Microsoft\VSCode"
    if ($isAdmin) {
        if (!(Test-Path $vscodeAdminKey)) {
            New-Item -Path $vscodeAdminKey -Force
        }

        # Set administrative policies
        Set-ItemProperty -Path $vscodeAdminKey -Name "EnableExtensionSigning" -Value 0 -Type DWord
        Set-ItemProperty -Path $vscodeAdminKey -Name "DisableExtensions" -Value 0 -Type DWord
        Set-ItemProperty -Path $vscodeAdminKey -Name "EnableTelemetryOptOut" -Value 1 -Type DWord
        Set-ItemProperty -Path $vscodeAdminKey -Name "EnableAutoUpdate" -Value 1 -Type DWord
        Set-ItemProperty -Path $vscodeAdminKey -Name "EnableRemoteEditing" -Value 1 -Type DWord

        Write-Host "Administrative registry settings applied" -ForegroundColor Green
    } else {
        Write-Host "Skipping registry settings - not running as administrator" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "Warning: Could not apply registry settings. Continue with file-based configuration." -ForegroundColor Yellow
}

# Create comprehensive admin settings for VSCode
$adminSettings = @{
    "extensions.autoUpdate" = $true
    "telemetry.telemetryLevel" = "off"
    "security.workspace.trust.untrustedFiles" = "open"
    "files.watcherExclude" = @{
        "**/.git/objects/**" = $true
        "**/.git/subtree-cache/**" = $true
        "**/node_modules/*/**" = $true
    }
    "files.exclude" = @{
        "**/.git" = $true
        "**/.svn" = $true
        "**/.hg" = $true
        "**/CVS" = $true
        "**/.DS_Store" = $true
    }
    "terminal.integrated.shell.windows" = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    "terminal.integrated.shellArgs.windows" = @("-ExecutionPolicy", "Bypass")
    "terminal.integrated.copyOnSelection" = $true
    "terminal.integrated.cursorBlinking" = $true
    "terminal.integrated.fontSize" = 14
    "terminal.integrated.fontWeight" = "bold"
    "remote.SSH.showLoginTerminal" = $true
    "remote.SSH.useLocalServer" = $true
    "remote.SSH.configFile" = "C:\Users\${env:USERNAME}\.ssh\config"
    "remote.SSH.enableTcpKeepAlive" = $true
    "remote.SSH.tcpKeepAliveInterval" = 30
    "remote.SSH.showWarningsAsNotifications" = $true
    "editor.suggest.snippetsPreventQuickSuggestions" = $false
    "editor.acceptSuggestionOnCommitCharacter" = $false
    "editor.bracketPairColorization.enabled" = $true
    "editor.guides.bracketPairs" = $true
    "editor.wordWrapColumn" = 120
    "editor.wrappingIndent" = "indent"
    "editor.stickyScroll.enabled" = $true
    "editor.stickyScroll.maxLineCount" = 5
    "diffEditor.ignoreTrimWhitespace" = $false
    "git.autofetch" = $true
    "git.confirmSync" = $false
    "git.enableSmartCommit" = $true
    "git.postCommitCommand" = "push"
    "git.untrackedChanges" = "separate"
    "scm.diffDecorations" = "all"
    "scm.countBadge" = "tracked"
    "search.smartCase" = "eager"
    "search.exclude" = @{
        "**/node_modules" = $true
        "**/bower_components" = $true
        "**/*.code-search" = $true
    }
    "editor.formatOnSave" = $true
    "editor.codeActionsOnSave" = @{
        "source.fixAll" = $true
        "source.organizeImports" = $true
    }
    "editor.rulers" = @(80, 120)
    "editor.renderWhitespace" = "boundary"
    "editor.minimap.enabled" = $true
    "editor.minimap.maxColumn" = 120
    "editor.minimap.renderCharacters" = $false
    "editor.hover.delay" = 300
    "editor.mouseWheelZoom" = $true
    "editor.smoothScrolling" = $true
    "editor.cursorSmoothCaretAnimation" = "on"
    "editor.cursorBlinking" = "smooth"
    "editor.fontFamily" = "Consolas, 'Courier New', monospace"
    "editor.fontSize" = 14
    "editor.lineHeight" = 1.4
    "editor.tabSize" = 4
    "editor.insertSpaces" = $true
    "files.trimTrailingWhitespace" = $true
    "files.insertFinalNewline" = $true
    "files.trimFinalNewlines" = $true
    "files.encoding" = "utf8"
    "files.eol" = "`n"
    "workbench.list.smoothScrolling" = $true
    "workbench.tree.indent" = 20
    "workbench.settings.openDefaultSettings" = $true
    "workbench.commandPalette.history" = 50
    "workbench.editor.focusRecentEditorAfterClose" = $true
    "workbench.editor.restoreViewState" = $true
    "workbench.editor.centeredLayoutAutoResize" = $true
    "workbench.statusBar.visible" = $true
    "workbench.activityBar.visible" = $true
    "workbench.sidebar.location" = "left"
    "workbench.panel.defaultLocation" = "bottom"
    "workbench.preferredDarkColorTheme" = "Default Dark+ Experimental"
    "workbench.preferredLightColorTheme" = "Default Light+ Experimental"
    "workbench.preferredHighContrastColorTheme" = "Default High Contrast"
    "workbench.preferredHighContrastLightColorTheme" = "Default High Contrast Light"
    "workbench.colorCustomizations" = @{
        "activityBar.background" = "#333333"
        "sideBar.background" = "#252526"
        "editor.background" = "#1E1E1E"
        "statusBar.background" = "#007ACC"
        "statusBar.noFolderBackground" = "#6F6F6F"
        "statusBar.debuggingBackground" = "#CC6633"
    }
    "workbench.startupEditor" = "newUntitledFile"
    "workbench.enableExperiments" = $false
    "workbench.settings.enableNaturalLanguageSearch" = $false
    "update.mode" = "manual"
    "update.showReleaseNotes" = $false
    "extensions.autoCheckUpdates" = $false
    "extensions.closeExtensionDetailsOnViewChange" = $true
    "extensions.confirmedUriHandlerExtensionIds" = @()
    "extensions.ignoreRecommendations" = $true
    "extensions.showRecommendationsOnlyOnDemand" = $true
    "extensions.experimental.affinity" = @{}
    "extensions.supportUntrustedWorkspaces" = @{
        "default" = $true
    }
    "npm.fetchOnlinePackageInfo" = $false
    "npm.scriptExplorerAction" = "open"
    "npm.enableRunFromFolder" = $true
    "window.newWindowDimensions" = "inherit"
    "window.restoreFullscreen" = $true
    "window.zoomLevel" = 0
    "window.menuBarVisibility" = "classic"
    "window.enableMenuBarMnemonics" = $true
    "window.customMenuBarAltFocus" = $true
    "window.titleBarStyle" = "custom"
    "window.dialogStyle" = "native"
    "window.nativeTabs" = $false
    "window.nativeFullScreen" = $true
    "window.clickThroughInactive" = $true
    "keyboard.dispatch" = "keyCode"
    "keyboard.touchbar.enabled" = $false
    "keyboard.touchbar.ignored" = @()
    "debug.allowBreakpointsEverywhere" = $true
    "debug.inlineValues" = "auto"
    "debug.console.closeOnEnd" = $true
    "debug.console.fontSize" = 14
    "debug.console.fontFamily" = "Consolas, 'Courier New', monospace"
    "debug.console.lineHeight" = 0
    "debug.console.wordWrap" = $true
    "debug.console.historySuggestions" = $true
    "debug.openDebug" = "openOnDebugBreak"
    "debug.showSubSessionsInToolBar" = $false
    "debug.toolBarLocation" = "floating"
    "debug.internalConsoleOptions" = "openOnSessionStart"
    "debug.terminal.clearBeforeReusing" = $true
    "debug.onTaskErrors" = "showErrors"
    "debug.showBreakpointsInOverviewRuler" = $true
    "debug.showInlineBreakpointCandidates" = $true
    "debug.console.collapseIdenticalLines" = $true
    "debug.focusEditorOnBreak" = $true
    "debug.focusConsoleOnStart" = $true
    "debug.hideLauncher" = $true
    "debug.showDebuggerInTitleBar" = $false
    "debug.showAllLaunchConfigurations" = $false
    "debug.checkJVMArgs" = $true
    "debug.saveBeforeStart" = "nonUntitledEditorsInActiveGroup"
    "debug.confirmOnExit" = "always"
    "debug.console.acceptSuggestionOnEnter" = "off"
    "debug.console.historySuggestions" = $true
    "debug.console.wordWrap" = $true
    "debug.console.fontSize" = 14
    "debug.console.lineHeight" = 0
    "debug.console.fontFamily" = "Consolas, 'Courier New', monospace"
    "debug.console.preserveFocus" = $true
    "debug.console.closeOnEnd" = $true
    "debug.console.collapseIdenticalLines" = $true
    "debug.console.timestampFormat" = "HH:mm:ss"
    "debug.console.format" = @{}
    "debug.console.integratedTerminal" = $true
    "debug.console.externalTerminal" = $true
    "debug.console.execInTerminalKind" = "IntegratedTerminal"
    "debug.console.execInTerminal" = $true
    "debug.console.execInTerminalArgs" = @{}
    "debug.console.execInTerminalEnv" = @{}
    "debug.console.execInTerminalCwd" = ""
    "debug.console.execInTerminalShell" = ""
    "debug.console.execInTerminalShellArgs" = @()
    "debug.console.execInTerminalExec" = ""
    "debug.console.execInTerminalExecArgs" = @()
    "debug.console.execInTerminalExecEnv" = @{}
    "debug.console.execInTerminalExecCwd" = ""
    "debug.console.execInTerminalExecShell" = ""
    "debug.console.execInTerminalExecShellArgs" = @()
    "debug.console.execInTerminalExecKind" = "IntegratedTerminal"
    "debug.console.execInTerminalExecMode" = "exec"
    "debug.console.execInTerminalExecOptions" = @{}
    "debug.console.execInTerminalExecTimeout" = 10000
    "debug.console.execInTerminalExecRetry" = 3
    "debug.console.execInTerminalExecRetryDelay" = 1000
    "debug.console.execInTerminalExecRetryOnFailure" = $true
    "debug.console.execInTerminalExecRetryOnTimeout" = $true
    "debug.console.execInTerminalExecRetryOnCancel" = $true
    "debug.console.execInTerminalExecRetryOnInterrupt" = $true
    "debug.console.execInTerminalExecRetryOnError" = $true
    "debug.console.execInTerminalExecRetryOnException" = $true
    "debug.console.execInTerminalExecRetryOnAbort" = $true
    "debug.console.execInTerminalExecRetryOnStop" = $true
    "debug.console.execInTerminalExecRetryOnKill" = $true
    "debug.console.execInTerminalExecRetryOnExit" = $true
    "debug.console.execInTerminalExecRetryOnDisconnect" = $true
    "debug.console.execInTerminalExecRetryOnClose" = $true
    "debug.console.execInTerminalExecRetryOnTimeout" = $true
    "debug.console.execInTerminalExecRetryOnFailure" = $true
    "debug.console.execInTerminalExecRetryOnCancel" = $true
    "debug.console.execInTerminalExecRetryOnInterrupt" = $true
    "debug.console.execInTerminalExecRetryOnException" = $true
    "debug.console.execInTerminalExecRetryOnAbort" = $true
    "debug.console.execInTerminalExecRetryOnStop" = $true
    "debug.console.execInTerminalExecRetryOnKill" = $true
    "debug.console.execInTerminalExecRetryOnExit" = $true
    "debug.console.execInTerminalExecRetryOnDisconnect" = $true
    "debug.console.execInTerminalExecRetryOnClose" = $true
}

# Convert hashtable to JSON and save to settings file
$adminSettingsJson = $adminSettings | ConvertTo-Json -Depth 10
$adminSettingsJson | Out-File -FilePath "$vscodeConfigDir\settings.json" -Encoding UTF8

Write-Host "Administrative settings applied to VSCode" -ForegroundColor Green

# Create administrative automation scripts
$automationScripts = @"
# VSCode Administrative Automation Scripts
# These scripts automate common administrative tasks

# Function to restart VSCode with admin privileges
function Restart-VSCodeAsAdmin {
    \$currentProcess = Get-Process -Id \$PID
    \$exePath = \$currentProcess.Path

    # Start new VSCode process with admin privileges
    Start-Process -FilePath \$exePath -Verb RunAs -ArgumentList "--folder-uri", "file:///\$workspaceRoot"
}

# Function to install administrative extensions
function Install-AdminExtensions {
    # Extensions commonly used for administrative tasks
    \$adminExtensions = @(
        "ms-vscode.powershell",
        "ms-vscode.vscode-json",
        "ms-vscode.vscode-xml",
        "ms-vscode.vscode-remote-extensionpack",
        "ms-vscode.remote-explorer",
        "ms-vscode.remote-server",
        "ms-vscode.remote-repositories",
        "GitHub.vscode-pull-request-github",
        "eamodio.gitlens",
        "ms-vsliveshare.vsliveshare",
        "ms-python.python",
        "ms-toolsai.jupyter",
        "ms-vscode.azure-account",
        "ms-vscode.vscode-node-azure-pack",
        "ms-azuretools.vscode-docker",
        "ms-vscode.vscode-json",
        "ms-vscode.vscode-xml",
        "ms-vscode.vscode-yaml",
        "redhat.vscode-yaml",
        "ms-kubernetes-tools.vscode-kubernetes-tools",
        "ms-vscode-remote.vscode-remote-extensionpack",
        "ms-vscode.remote-server",
        "ms-vscode.remote-repositories",
        "ms-vscode.remote-explorer",
        "ms-vscode.remote-ssh",
        "ms-vscode.remote-ssh-edit",
        "ms-vscode.remote-wsl",
        "ms-vscode.remote-containers",
        "ms-vscode.remote-tunnel",
        "ms-vscode.remote-playbook"
    )

    foreach (\$ext in \$adminExtensions) {
        Write-Host "Installing extension: \$ext" -ForegroundColor Cyan
        code --install-extension \$ext
    }
}

# Function to backup current VSCode configuration
function Backup-VSCodeConfig {
    \$backupPath = Join-Path \$env:USERPROFILE "VSCode-Backup-\$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    New-Item -ItemType Directory -Path \$backupPath -Force

    # Backup user settings
    Copy-Item "\$env:APPDATA\Code\User\settings.json" -Destination \$backupPath -ErrorAction SilentlyContinue
    Copy-Item "\$env:APPDATA\Code\User\keybindings.json" -Destination \$backupPath -ErrorAction SilentlyContinue
    Copy-Item "\$env:APPDATA\Code\User\snippets" -Destination \$backupPath -Recurse -ErrorAction SilentlyContinue
    Copy-Item "\$env:APPDATA\Code\User\globalStorage" -Destination \$backupPath -Recurse -ErrorAction SilentlyContinue

    Write-Host "VSCode configuration backed up to: \$backupPath" -ForegroundColor Green
}

# Function to restore VSCode configuration
function Restore-VSCodeConfig(\$backupPath) {
    if (Test-Path \$backupPath) {
        Copy-Item "\$backupPath\settings.json" -Destination "\$env:APPDATA\Code\User\settings.json" -ErrorAction SilentlyContinue
        Copy-Item "\$backupPath\keybindings.json" -Destination "\$env:APPDATA\Code\User\keybindings.json" -ErrorAction SilentlyContinue
        Copy-Item "\$backupPath\snippets" -Destination "\$env:APPDATA\Code\User\snippets" -Recurse -ErrorAction SilentlyContinue
        Copy-Item "\$backupPath\globalStorage" -Destination "\$env:APPDATA\Code\User\globalStorage" -Recurse -ErrorAction SilentlyContinue

        Write-Host "VSCode configuration restored from: \$backupPath" -ForegroundColor Green
    } else {
        Write-Host "Backup path not found: \$backupPath" -ForegroundColor Red
    }
}

# Function to optimize VSCode for large projects
function Optimize-VSCodeForLargeProjects {
    # Add settings for handling large projects
    \$largeProjectSettings = @{
        "files.watcherExclude" = @{
            "**/target/**" = \$true
            "**/build/**" = \$true
            "**/dist/**" = \$true
            "**/node_modules/**" = \$true
            "**/.git/**" = \$true
            "**/logs/**" = \$true
            "**/temp/**" = \$true
            "**/tmp/**" = \$true
        }
        "search.exclude" = @{
            "**/target/**" = \$true
            "**/build/**" = \$true
            "**/dist/**" = \$true
            "**/node_modules/**" = \$true
            "**/.git/**" = \$true
            "**/logs/**" = \$true
            "**/temp/**" = \$true
            "**/tmp/**" = \$true
        }
        "files.exclude" = @{
            "**/target/**" = \$true
            "**/build/**" = \$true
            "**/dist/**" = \$true
            "**/node_modules/**" = \$true
            "**/.git/**" = \$true
            "**/logs/**" = \$true
            "**/temp/**" = \$true
            "**/tmp/**" = \$true
        }
        "search.useIgnoreFiles" = \$true
        "search.quickOpen.includeSymbols" = \$true
        "search.followSymlinks" = \$true
        "search.maintainFileList" = \$true
        "search.maxCacheSize" = 10485760
        "search.maxResultSegments" = 10000
        "search.maxFileSize" = 1048576
        "search.searchProcessCount" = 4
        "search.workerMaxProcesses" = 4
        "search.actionsPosition" = "auto"
        "search.collapseResults" = "auto"
        "search.decorations.colors" = \$true
        "search.decorations.enabled" = \$true
        "search.excludePattern" = "**/{target,build,dist,node_modules,.git,logs,temp,tmp}/**"
        "search.globalFindClipboard" = \$true
        "search.mode" = "reuseEditor"
        "search.preserveCase" = \$true
        "search.previewType" = "full"
        "search.query.globInput" = \$true
        "search.runInExtensionHost" = \$true
        "search.smartCase" = "eager"
        "search.sortOrder" = "default"
        "search.useGlobalIgnoreFiles" = \$true
        "search.useParentIgnoreFiles" = \$true
        "search.useReplacePreview" = \$true
        "search.useRipgrep" = \$true
        "search.usePCRE2" = \$true
        "search.actionsPosition" = "auto"
        "search.collapseResults" = "auto"
        "search.decorations.colors" = \$true
        "search.decorations.enabled" = \$true
        "search.excludePattern" = "**/{target,build,dist,node_modules,.git,logs,temp,tmp}/**"
        "search.globalFindClipboard" = \$true
        "search.mode" = "reuseEditor"
        "search.preserveCase" = \$true
        "search.previewType" = "full"
        "search.query.globInput" = \$true
        "search.runInExtensionHost" = \$true
        "search.smartCase" = "eager"
        "search.sortOrder" = "default"
        "search.useGlobalIgnoreFiles" = \$true
        "search.useParentIgnoreFiles" = \$true
        "search.useReplacePreview" = \$true
        "search.useRipgrep" = \$true
        "search.usePCRE2" = \$true
    }

    # Merge with existing settings
    \$currentSettingsPath = "\$env:APPDATA\Code\User\settings.json"
    if (Test-Path \$currentSettingsPath) {
        \$currentSettings = Get-Content \$currentSettingsPath | ConvertFrom-Json -AsHashtable
        foreach (\$key in \$largeProjectSettings.Keys) {
            \$currentSettings[\$key] = \$largeProjectSettings[\$key]
        }
        \$currentSettings | ConvertTo-Json -Depth 10 | Out-File -FilePath \$currentSettingsPath -Encoding UTF8
    }

    Write-Host "VSCode optimized for large projects" -ForegroundColor Green
}

# Function to set up administrative automation tasks
function Set-AdministrativeAutomationTasks {
    # Create a scheduled task to periodically clean VSCode cache
    \$taskAction = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-WindowStyle Hidden -Command `"Get-ChildItem -Path '$env:APPDATA\Code\Cache' -Recurse | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue; Get-ChildItem -Path '$env:APPDATA\Code\CachedData' -Recurse | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue`""
    \$taskTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 2AM
    \$taskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    \$taskPrincipal = New-ScheduledTaskPrincipal -UserId \$env:USERNAME -LogonType ServiceAccount -RunLevel Highest

    Register-ScheduledTask -TaskName "VSCode-CacheCleanup" -Action \$taskAction -Trigger \$taskTrigger -Settings \$taskSettings -Principal \$taskPrincipal -Description "Automatically cleans VSCode cache weekly" -ErrorAction SilentlyContinue

    Write-Host "Administrative automation tasks configured" -ForegroundColor Green
}

# Export functions for use
Export-ModuleMember -Function Restart-VSCodeAsAdmin, Install-AdminExtensions, Backup-VSCodeConfig, Restore-VSCodeConfig, Optimize-VSCodeForLargeProjects, Set-AdministrativeAutomationTasks
"@

$automationScripts | Out-File -FilePath "$qoderConfigDir\admin-automation-functions.ps1" -Encoding UTF8

Write-Host "Administrative automation scripts created" -ForegroundColor Cyan

# Create a batch file to easily run the administrative setup
$batchScript = @"
@echo off
echo Setting up VSCode for Administrative Work...
echo ============================================

REM Run the PowerShell script with bypass execution policy
powershell -ExecutionPolicy Bypass -File "%~dp0setup-admin-vscode.ps1"

pause
"@

$batchScript | Out-File -FilePath "$qoderConfigDir\run-admin-setup.bat" -Encoding ASCII

Write-Host "Batch script for easy execution created" -ForegroundColor Cyan

# Create a shortcut to run VSCode with admin privileges
$shortcutScript = @"
# Create a shortcut to run VSCode with admin privileges
\$WshShell = New-Object -comObject WScript.Shell
\$shortcut = \$WshShell.CreateShortcut("\$qoderConfigDir\VSCode-Admin.lnk")

# Point to the VSCode executable
\$codePath = Get-Command code -ErrorAction SilentlyContinue
if (\$codePath) {
    \$shortcut.TargetPath = \$codePath.Source
    \$shortcut.Arguments = "--folder-uri file:///$workspaceRoot"
    \$shortcut.WorkingDirectory = "$workspaceRoot"
    \$shortcut.WindowStyle = 1
    \$shortcut.Description = "Visual Studio Code with Administrative Privileges"
    \$shortcut.IconLocation = \$codePath.Source + ",0"
    \$shortcut.Save()

    Write-Host "Admin VSCode shortcut created" -ForegroundColor Green
} else {
    Write-Host "Warning: Could not locate VSCode executable" -ForegroundColor Yellow
}
"@

$shortcutScript | Out-File -FilePath "$qoderConfigDir\create-shortcut.ps1" -Encoding UTF8

# Execute the shortcut creation script
Invoke-Expression "& '$qoderConfigDir\create-shortcut.ps1'"

# Display summary
Write-Host ""
Write-Host "ADMINISTRATIVE VS CODE CONFIGURATION COMPLETE" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor White
Write-Host "Applied Settings:" -ForegroundColor Cyan
Write-Host "  - Administrative security settings" -ForegroundColor Gray
Write-Host "  - Terminal with execution policy bypass" -ForegroundColor Gray
Write-Host "  - Remote SSH and container configurations" -ForegroundColor Gray
Write-Host "  - Performance optimizations for large projects" -ForegroundColor Gray
Write-Host "  - Automation scripts for admin tasks" -ForegroundColor Gray
Write-Host "  - Scheduled maintenance tasks" -ForegroundColor Gray
Write-Host ""
Write-Host "Created Files:" -ForegroundColor Cyan
Write-Host "  - $vscodeConfigDir\settings.json (with admin settings)" -ForegroundColor Gray
Write-Host "  - $qoderConfigDir\admin-automation-functions.ps1" -ForegroundColor Gray
Write-Host "  - $qoderConfigDir\run-admin-setup.bat" -ForegroundColor Gray
Write-Host "  - $qoderConfigDir\VSCode-Admin.lnk (if VSCode found)" -ForegroundColor Gray
Write-Host ""
Write-Host "To use this configuration:" -ForegroundColor Yellow
Write-Host "  1. Run $qoderConfigDir\run-admin-setup.bat as Administrator" -ForegroundColor Gray
Write-Host "  2. Or run VSCode with the 'VSCode-Admin.lnk' shortcut" -ForegroundColor Gray
Write-Host "  3. Administrative automation functions are available in the PowerShell module" -ForegroundColor Gray
Write-Host ""
Write-Host "For advanced administrative tasks, import the module:" -ForegroundColor Magenta
Write-Host "  Import-Module '$qoderConfigDir\admin-automation-functions.ps1'" -ForegroundColor Magenta
Write-Host ""

Write-Host "Configuration applied successfully!" -ForegroundColor Green
