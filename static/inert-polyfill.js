/**
 * Inert attribute polyfill for older browsers
 * The inert attribute makes elements unfocusable and hidden from assistive tech
 */
(function() {
    // Check if inert is supported
    if ('inert' in HTMLElement.prototype) {
        return;
    }

    // Define inert property
    Object.defineProperty(HTMLElement.prototype, 'inert', {
        get: function() {
            return this.hasAttribute('inert');
        },
        set: function(value) {
            if (value) {
                this.setAttribute('inert', '');
            } else {
                this.removeAttribute('inert');
            }
        }
    });

    // Handle inert attribute changes
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'attributes' && mutation.attributeName === 'inert') {
                const target = mutation.target;
                if (target.hasAttribute('inert')) {
                    makeInert(target);
                } else {
                    makeNonInert(target);
                }
            }
        });
    });

    function makeInert(element) {
        // Store current tabindex values
        const focusableElements = element.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        focusableElements.forEach((el) => {
            if (!el.hasAttribute('data-original-tabindex')) {
                const currentTabIndex = el.getAttribute('tabindex');
                el.setAttribute('data-original-tabindex', currentTabIndex || '0');
            }
            el.setAttribute('tabindex', '-1');
        });

        // Add aria-hidden for accessibility
        if (!element.hasAttribute('data-original-aria-hidden')) {
            const currentAriaHidden = element.getAttribute('aria-hidden');
            element.setAttribute('data-original-aria-hidden', currentAriaHidden || '');
        }
        element.setAttribute('aria-hidden', 'true');

        // Add visual indication
        element.style.pointerEvents = 'none';
    }

    function makeNonInert(element) {
        // Restore tabindex values
        const focusableElements = element.querySelectorAll('[data-original-tabindex]');
        
        focusableElements.forEach((el) => {
            const originalTabIndex = el.getAttribute('data-original-tabindex');
            if (originalTabIndex && originalTabIndex !== '0') {
                el.setAttribute('tabindex', originalTabIndex);
            } else if (originalTabIndex === '0') {
                el.removeAttribute('tabindex');
            }
            el.removeAttribute('data-original-tabindex');
        });

        // Restore aria-hidden
        const originalAriaHidden = element.getAttribute('data-original-aria-hidden');
        if (originalAriaHidden === '') {
            element.removeAttribute('aria-hidden');
        } else if (originalAriaHidden) {
            element.setAttribute('aria-hidden', originalAriaHidden);
        }
        element.removeAttribute('data-original-aria-hidden');

        // Remove visual indication
        element.style.pointerEvents = '';
    }

    // Observe all tab-content sections
    document.querySelectorAll('.tab-content').forEach((section) => {
        observer.observe(section, { attributes: true });
        
        // Initial setup
        if (section.hasAttribute('inert')) {
            makeInert(section);
        }
    });

    // Also observe dynamically added elements
    const bodyObserver = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    if (node.classList && node.classList.contains('tab-content')) {
                        observer.observe(node, { attributes: true });
                        if (node.hasAttribute('inert')) {
                            makeInert(node);
                        }
                    }
                    
                    // Check children
                    if (node.querySelectorAll) {
                        node.querySelectorAll('.tab-content').forEach((section) => {
                            observer.observe(section, { attributes: true });
                            if (section.hasAttribute('inert')) {
                                makeInert(section);
                            }
                        });
                    }
                }
            });
        });
    });

    if (document.body) {
        bodyObserver.observe(document.body, { childList: true, subtree: true });
    } else {
        window.addEventListener('DOMContentLoaded', () => {
            bodyObserver.observe(document.body, { childList: true, subtree: true });
        });
    }
})();
