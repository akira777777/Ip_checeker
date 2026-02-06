# Скрипт для запрета редакторов в окнах KimiCode
# Disable KimiCode Editor Windows Script

Write-Host "Запрещаем появление редакторов в окнах KimiCode..." -ForegroundColor Green
Write-Host ""

# Пути к файлам настроек
$WorkspaceSettings = Join-Path $PSScriptRoot "workspace-layout.code-workspace"
$VSCodeSettings = Join-Path $PSScriptRoot "..\.vscode\settings.json"

Write-Host "Обновляем настройки рабочей области..." -ForegroundColor Yellow

# Создаем резервные копии
if (Test-Path $WorkspaceSettings) {
    $WorkspaceBackup = "$WorkspaceSettings.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $WorkspaceSettings $WorkspaceBackup -Force
    Write-Host "Резервная копия рабочей области: $WorkspaceBackup" -ForegroundColor Cyan
}

if (Test-Path $VSCodeSettings) {
    $VSCodeBackup = "$VSCodeSettings.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $VSCodeSettings $VSCodeBackup -Force
    Write-Host "Резервная копия VS Code настроек: $VSCodeBackup" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Настройки успешно применены!" -ForegroundColor Green
Write-Host "Ключевые изменения:"
Write-Host "- workbench.editor.limit.enabled: true"
Write-Host "- workbench.editor.limit.value: 1"
Write-Host "- kimi-code.disableEditorPopups: true"
Write-Host "- kimi-code.preventEditorWindows: true"
Write-Host ""

Write-Host "Перезапустите VS Code чтобы изменения вступили в силу" -ForegroundColor Yellow
Write-Host "Или используйте Ctrl+Shift+P -> 'Developer: Reload Window'" -ForegroundColor Cyan

Write-Host ""
Write-Host "Нажмите любую клавишу для продолжения..." -NoNewline
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")