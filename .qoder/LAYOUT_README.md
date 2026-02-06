# QODER Layout Configuration

This directory contains configuration files to maintain consistent layout and equal spacing in QODER.

## Files Included

- `layout-config.json` - Main layout configuration with spacing and appearance settings
- `workspace-layout.code-workspace` - Workspace template with predefined panel arrangement  
- `apply-layout.bat` - Windows batch script to apply settings
- `apply-layout.ps1` - PowerShell script for advanced configuration

## Key Features Configured

### Equal Spacing
- Fixed panel widths with distribute sizing
- Consistent margins and padding (16px elements, 8px lists)
- Grid-based layout with insertion indicators
- Equal gaps between panels (12px)

### Tab Layout
- Fixed tab width sizing
- Close buttons always on the right
- No tab wrapping
- Consistent pinned tab sizing

### Panel Management
- Bottom panel positioning
- Distribute split sizing for equal space
- No auto-resize of centered layouts
- Empty groups remain open

### Appearance Consistency
- Uniform tree indentation (8px)
- Consistent list padding (4px)
- Always visible indent guides
- Fixed terminal tab behavior

## Usage

1. **Automatic Application**: Run `apply-layout.ps1` or `apply-layout.bat`
2. **Manual Configuration**: Open `.vscode/settings.json` in your workspace
3. **Workspace Template**: Use `workspace-layout.code-workspace` as your workspace file

## Settings Explanation

```json
{
  // Layout and Spacing Configuration
  "workbench.panel.defaultLocation": "bottom",
  "workbench.editor.tabSizing": "fixed",
  "workbench.editor.splitSizing": "distribute",
  
  // Equal spacing enforcement
  "workbench.grid.insertionIndicator": true,
  "workbench.list.padding": 4,
  "workbench.tree.indent": 8,
  
  // Permanent window arrangement
  "window.restoreWindows": "all",
  "workbench.editor.restoreViewState": true
}
```

## Maintenance

The configuration will persist across QODER restarts. To modify:
1. Edit the settings in `.vscode/settings.json`
2. Run the apply script to ensure changes take effect
3. Restart QODER to see updates

## Troubleshooting

If layout issues occur:
1. Check that all configuration files are present
2. Run the apply script to reconfigure
3. Clear QODER's workspace state cache if needed
4. Verify no conflicting extensions are overriding settings