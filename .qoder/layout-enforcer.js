// QODER Layout Enforcement Script
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
window.addEventListener('focus', enforceEqualSpacing);
