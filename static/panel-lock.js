// Panel Layout Lock Configuration
// This script ensures three panels remain fixed with equal spacing

(function() {
    'use strict';
    
    // Configuration for fixed panel layout
    const FIXED_LAYOUT_CONFIG = {
        // CSS classes to apply
        classes: ['fixed-panel-layout', 'locked-panel', 'equal-spacing', 'no-auto-generation'],
        
        // Panel selectors to target
        selectors: [
            '.main-content',
            '.app-container', 
            '[class*="panel"]',
            '.editor-container',
            '.workbench'
        ],
        
        // Child panel selectors
        childSelectors: [
            ':scope > *',
            '.panel',
            '.editor-group',
            '.view-item'
        ]
    };
    
    // Apply fixed layout to panels
    function lockPanelLayout() {
        console.log('Locking panel layout...');
        
        // Find the main container
        let mainContainer = null;
        for (const selector of FIXED_LAYOUT_CONFIG.selectors) {
            mainContainer = document.querySelector(selector);
            if (mainContainer) {
                console.log(`Found container with selector: ${selector}`);
                break;
            }
        }
        
        if (!mainContainer) {
            console.warn('No suitable container found for panel locking');
            return;
        }
        
        // Apply main layout classes
        FIXED_LAYOUT_CONFIG.classes.forEach(className => {
            mainContainer.classList.add(className);
        });
        
        // Lock child panels
        const childPanels = mainContainer.querySelectorAll(FIXED_LAYOUT_CONFIG.childSelectors.join(', '));
        console.log(`Found ${childPanels.length} child panels to lock`);
        
        childPanels.forEach((panel, index) => {
            panel.classList.add('locked-panel');
            
            // Apply CSS overrides to prevent changes
            const style = panel.style;
            style.setProperty('transition', 'none', 'important');
            style.setProperty('flex', '1', 'important');
            style.setProperty('min-width', '0', 'important');
            style.setProperty('max-width', 'none', 'important');
            style.setProperty('position', 'static', 'important');
            style.setProperty('resize', 'none', 'important');
            
            console.log(`Locked panel ${index + 1}`);
        });
        
        // Prevent future modifications
        observeMutations(mainContainer);
        
        console.log('Panel layout locked successfully!');
    }
    
    // Observe DOM mutations to prevent dynamic changes
    function observeMutations(target) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList') {
                    // Reapply fixed layout if children change
                    lockPanelLayout();
                } else if (mutation.type === 'attributes') {
                    // Prevent attribute changes that affect layout
                    const element = mutation.target;
                    if (element.classList.contains('locked-panel')) {
                        // Restore locked properties
                        const style = element.style;
                        style.setProperty('transition', 'none', 'important');
                        style.setProperty('flex', '1', 'important');
                        style.setProperty('min-width', '0', 'important');
                        style.setProperty('max-width', 'none', 'important');
                    }
                }
            });
        });
        
        observer.observe(target, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['class', 'style', 'width', 'height']
        });
    }
    
    // Initialize when DOM is ready
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', lockPanelLayout);
        } else {
            lockPanelLayout();
        }
        
        // Also run after a short delay to catch dynamic content
        setTimeout(lockPanelLayout, 1000);
    }
    
    // Export for external use
    window.PanelLayoutLocker = {
        lock: lockPanelLayout,
        config: FIXED_LAYOUT_CONFIG
    };
    
    // Auto-initialize
    init();
    
})();