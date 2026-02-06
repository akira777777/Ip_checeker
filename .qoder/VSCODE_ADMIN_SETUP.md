# VSCode Administrative Setup for Automated Work

This configuration sets up Visual Studio Code for optimal automated administrative work with full administrator privileges and comprehensive automation capabilities.

## Features

### Administrative Privileges

- Configured to run with elevated permissions
- Access to system-level operations
- Ability to modify protected system files
- Registry access for advanced configuration

### Automation Capabilities

- Automated extension updates
- Automatic code formatting on save
- Integrated terminal with execution policy bypass
- Remote SSH and container management
- Scheduled maintenance tasks

### Enhanced Terminal Configuration

- PowerShell with execution policy bypass
- Administrative PowerShell profile loaded automatically
- Custom aliases for common administrative tasks
- Optimized terminal appearance and functionality

### Security Settings

- Disabled telemetry for privacy
- Open untrusted files in workspace
- Secure extension management
- Protected against unwanted changes

## Setup Instructions

### Prerequisites

- Visual Studio Code installed
- Administrative rights on the system
- PowerShell execution policy allowing script execution

### Installation

1. **Run the setup script as Administrator**:

   ```
   Right-click on "run-admin-setup.bat" and select "Run as administrator"
   ```

2. **Or manually execute the PowerShell script**:

   ```powershell
   # Navigate to the .qoder directory
   cd d:\Ip_checeker\.qoder

   # Run the setup script with execution policy bypass
   powershell -ExecutionPolicy Bypass -File ".\setup-admin-vscode.ps1"
   ```

3. **Restart VS Code** to apply all settings

## Usage

### Starting VSCode with Administrative Privileges

- Use the `VSCode-Admin.lnk` shortcut (created during setup)
- Or run `Start-VSCodeAsAdmin` from the PowerShell terminal
- Or run `code --folder-uri file:///d:/Ip_checeker` as administrator

### Available Administrative Functions

After loading the profile, the following functions are available:

- `Show-AdminStatus` - Shows current administrative status
- `Start-VSCodeAsAdmin` - Starts VSCode with administrative privileges
- `Get-AdminVSCodeSettings` - Shows current VSCode administrative settings
- `Test-AdminCapabilities` - Tests available administrative capabilities
- `Restart-VSCodeAsAdmin` - Restarts VSCode with admin privileges (from admin module)
- `Install-AdminExtensions` - Installs recommended admin extensions (from admin module)
- `Backup-VSCodeConfig` - Backs up VSCode configuration (from admin module)
- `Restore-VSCodeConfig` - Restores VSCode configuration (from admin module)
- `Optimize-VSCodeForLargeProjects` - Optimizes VSCode for large projects (from admin module)
- `Set-AdministrativeAutomationTasks` - Configures admin automation tasks (from admin module)

### Quick Aliases

- `vscadmin` - Alias for the code command
- `vscconf` - Opens the VSCode settings file
- `vscws` - Opens the workspace settings file

## Configuration Files

- `settings.json` - Contains VSCode administrative settings
- `workspace-layout.code-workspace` - Workspace configuration with admin features
- `setup-admin-vscode.ps1` - Main setup script
- `admin-automation-functions.ps1` - Administrative automation functions
- `Microsoft.PowerShell_profile.ps1` - PowerShell profile for admin tasks
- `run-admin-setup.bat` - Batch file to run setup easily
- `create-shortcut.ps1` - Creates admin shortcut

## Security Considerations

- This configuration disables some security features to enable administrative tasks
- Only run with administrative privileges when necessary
- Review all scripts before execution
- Regularly audit administrative access logs

## Troubleshooting

### If VSCode doesn't start with administrative privileges

1. Manually run VSCode as administrator
2. Check that the shortcut was created properly
3. Verify UAC settings allow elevation

### If PowerShell execution is blocked

1. Run: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`
2. Or run VSCode with the `--disable-gpu` flag

### If extensions don't install automatically

1. Manually install from the Extensions panel
2. Check network connectivity and firewall settings
3. Run the Install-AdminExtensions function manually

## Maintenance

The setup includes automated maintenance tasks:

- Weekly cache cleanup via scheduled task
- Automatic backup of settings
- Extension auto-updates
- Performance optimization

For manual maintenance, run the appropriate functions from the admin module.

---

**Note**: This configuration is designed for trusted environments. Use with caution on production systems.
