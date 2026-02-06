/* UI shell: navigation, theme toggle, and light helpers - Fixed and Improved */

document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".tab-content");
    const navItems = document.querySelectorAll(".nav-item");
    const pageTitle = document.getElementById("page-title");

    // Check required elements exist
    if (!tabs.length || !navItems.length) {
        console.warn("[script.js] Required tab elements not found");
        return;
    }

    function activateTab(id) {
        if (!id) {
            console.warn("[activateTab] No tab ID provided");
            return;
        }

        // Hide all tabs
        tabs.forEach((t) => {
            t.classList.remove("active");
            t.setAttribute("aria-hidden", "true");
        });
        
        // Deactivate all nav items
        navItems.forEach((n) => {
            n.classList.remove("active");
            n.setAttribute("aria-selected", "false");
            n.setAttribute("tabindex", "-1");
        });
        
        // Activate target tab
        const target = document.getElementById(id);
        const nav = document.querySelector(`.nav-item[data-tab="${id}"]`);
        
        if (target) {
            target.classList.add("active");
            target.removeAttribute("aria-hidden");
        } else {
            console.warn(`[activateTab] Tab content not found: ${id}`);
        }
        
        if (nav) {
            nav.classList.add("active");
            nav.setAttribute("aria-selected", "true");
            nav.setAttribute("tabindex", "0");
            nav.focus();
        } else {
            console.warn(`[activateTab] Nav item not found: ${id}`);
        }
        
        // Update page title
        if (pageTitle) {
            const navText = nav?.querySelector("span")?.textContent?.trim() || id;
            pageTitle.textContent = navText;
        }
        
        // Save active tab
        try {
            localStorage.setItem("ipchecker-active-tab", id);
        } catch (e) {
            console.warn("[activateTab] Failed to save tab state:", e);
        }

        // Handle map tab visibility
        if (id === "map") {
            handleMapTabActivation();
        }

        // Lazy-init heavy resources for the active tab
        if (window.App?.lazyInitTab) {
            window.App.lazyInitTab(id);
        }
    }

    function handleMapTabActivation() {
        // Delay to allow tab to become visible
        setTimeout(() => {
            if (window.App?.state?.map) {
                try {
                    window.App.state.map.invalidateSize();
                } catch (err) {
                    console.warn("[handleMapTabActivation] Error invalidating map size:", err);
                }
            } else if (window.App?.initMap && typeof L !== "undefined") {
                try {
                    window.App.initMap();
                } catch (err) {
                    console.warn("[handleMapTabActivation] Error initializing map:", err);
                }
            }
        }, 100);
    }

    // Bind click events to nav items
    navItems.forEach((btn) => {
        btn.addEventListener("click", () => {
            const tabId = btn.getAttribute("data-tab");
            if (tabId) {
                activateTab(tabId);
            }
        });
    });

    // Keyboard navigation for sidebar
    const sidebarNav = document.querySelector(".sidebar-nav");
    if (sidebarNav) {
        sidebarNav.addEventListener("keydown", (e) => {
            const current = document.activeElement;
            const idx = Array.from(navItems).indexOf(current);
            if (idx === -1) return;

            switch (e.key) {
                case "ArrowRight":
                case "ArrowDown":
                    e.preventDefault();
                    const next = navItems[(idx + 1) % navItems.length];
                    next?.focus();
                    break;
                case "ArrowLeft":
                case "ArrowUp":
                    e.preventDefault();
                    const prev = navItems[(idx - 1 + navItems.length) % navItems.length];
                    prev?.focus();
                    break;
                case "Enter":
                case " ":
                    e.preventDefault();
                    current.click();
                    break;
                case "Home":
                    e.preventDefault();
                    navItems[0]?.focus();
                    break;
                case "End":
                    e.preventDefault();
                    navItems[navItems.length - 1]?.focus();
                    break;
            }
        });
    }

    // Restore or set default tab
    let initialTab = "dashboard";
    try {
        const savedTab = localStorage.getItem("ipchecker-active-tab");
        if (savedTab && document.getElementById(savedTab)) {
            initialTab = savedTab;
        }
    } catch (e) {
        console.warn("[script.js] Failed to load saved tab:", e);
    }
    activateTab(initialTab);

    // Refresh button
    const refreshBtn = document.getElementById("refresh-btn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            if (window.App?.runInvestigation) {
                window.App.runInvestigation(true);
            } else {
                console.warn("[refresh-btn] App not ready");
            }
        });
    }

    // IP input Enter key handler
    const ipInput = document.getElementById("ip-input");
    if (ipInput) {
        ipInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                const btnLookup = document.getElementById("btn-lookup");
                if (btnLookup) {
                    btnLookup.click();
                }
            }
        });

        // IP validation on blur
        ipInput.addEventListener("blur", () => {
            const value = ipInput.value.trim();
            if (value && window.App?.isValidIp && !window.App.isValidIp(value)) {
                ipInput.classList.add("invalid");
            } else {
                ipInput.classList.remove("invalid");
            }
        });
    }

    // Theme toggle
    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            document.body.classList.toggle("light-theme");
            const isLight = document.body.classList.contains("light-theme");
            
            const icon = themeToggle.querySelector("i");
            if (icon) {
                icon.className = isLight ? "fas fa-sun" : "fas fa-moon";
            }
            
            try {
                localStorage.setItem("ipchecker-theme", isLight ? "light" : "dark");
            } catch (e) {
                console.warn("[theme-toggle] Failed to save theme:", e);
            }
        });

        // Apply persisted theme
        try {
            const savedTheme = localStorage.getItem("ipchecker-theme");
            if (savedTheme === "light") {
                document.body.classList.add("light-theme");
                const icon = themeToggle.querySelector("i");
                if (icon) icon.className = "fas fa-sun";
            }
        } catch (e) {
            console.warn("[theme-toggle] Failed to load theme:", e);
        }
    }

    // Handle window resize for charts
    let resizeTimeout;
    window.addEventListener("resize", () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            if (window.App?.state?.charts) {
                Object.values(window.App.state.charts).forEach(chart => {
                    if (chart && typeof chart.resize === "function") {
                        chart.resize();
                    }
                });
            }
        }, 250);
    });

    // Visibility change handler - refresh data when tab becomes visible
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden && window.App?.runInvestigation) {
            // Optionally refresh data when returning to tab
            // Uncomment if desired:
            // window.App.runInvestigation(false);
        }
    });

    console.log("[script.js] UI shell initialized");
});

// Error handling for unhandled promise rejections
window.addEventListener("unhandledrejection", (event) => {
    console.error("[Unhandled Promise Rejection]", event.reason);
    if (window.App?.showToast) {
        window.App.showToast("An unexpected error occurred. Please try again.", "danger");
    }
});

// Error handling for uncaught errors
window.addEventListener("error", (event) => {
    console.error("[Uncaught Error]", event.error);
});
