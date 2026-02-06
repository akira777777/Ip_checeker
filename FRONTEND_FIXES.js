/*
 * Immediate fixes for IP Checker Pro frontend issues
 * This file contains patches for critical bugs and improvements
 */

// Patch 1: Enhanced error handling with logging
const EnhancedApp = {
    // ... existing App object properties
    
    async fetchJson(url, options = {}) {
        const { method = "GET", body } = options;
        try {
            const res = await fetch(url, {
                method,
                headers: { "Content-Type": "application/json" },
                body: body ? JSON.stringify(body) : undefined,
            });
            
            if (!res.ok) {
                const text = await res.text();
                const error = new Error(text || res.statusText);
                error.status = res.status;
                console.error(`API Error [${method} ${url}]:`, error);
                throw error;
            }
            
            const data = await res.json();
            console.debug(`API Success [${method} ${url}]:`, data);
            return data;
        } catch (err) {
            console.error(`Network Error [${method} ${url}]:`, err);
            throw err;
        }
    },

    // Patch 2: Safe localStorage handling
    init() {
        // Safely initialize lookupHistory
        try {
            const historyData = localStorage.getItem("ipchecker-history");
            this.state.lookupHistory = historyData ? JSON.parse(historyData) : [];
        } catch (err) {
            console.warn("Failed to parse lookup history:", err);
            this.state.lookupHistory = [];
            localStorage.setItem("ipchecker-history", "[]");
        }
        
        this.cacheDom();
        this.bindEvents();
        this.initCharts();
        this.initMap();
        this.renderHistory();
        this.runInvestigation();
    },

    // Patch 3: Robust DOM element caching with validation
    cacheDom() {
        this.el = {};
        const requiredElements = [
            'active-connections', 'secure-connections', 'warnings-count', 'threats-count',
            'connections-table', 'sys-hostname', 'sys-platform', 'sys-time', 'sys-interfaces',
            'interfaces-list', 'activity-list', 'scan-progress', 'progress-fill',
            'toast-container', 'loading-overlay', 'ip-input', 'lookup-results',
            'lookup-empty', 'recent-ips', 'mini-map', 'ips-input', 'security-score',
            'security-list', 'include-system', 'include-connections', 'include-security',
            'include-geolocation', 'report-results', 'export-buttons', 'history-list'
        ];

        requiredElements.forEach(id => {
            const element = document.getElementById(id);
            if (!element) {
                console.warn(`Required element not found: #${id}`);
            }
            this.el[id.replace(/-/g, '')] = element;
        });

        // Handle nested result fields
        this.el.resultFields = {};
        ['ip', 'flag', 'country', 'region', 'city', 'zip', 'coords', 
         'timezone', 'isp', 'org', 'asn', 'hostname'].forEach(field => {
            const element = document.getElementById(`result-${field}`);
            if (!element) {
                console.warn(`Result field element not found: #result-${field}`);
            }
            this.el.resultFields[field] = element;
        });
    },

    // Patch 4: Improved chart initialization with safety checks
    updateCharts(info) {
        const connections = info.connections || [];
        const tcp = connections.filter((c) => c.protocol === "TCP").length;
        const udp = connections.filter((c) => c.protocol === "UDP").length;
        const countries = (info.summary?.top_countries || []).filter(([name]) => name);

        // Safe chart initialization
        const connectionCtx = document.getElementById("connectionChart");
        if (connectionCtx && !this.state.charts.connections) {
            try {
                this.state.charts.connections = new Chart(connectionCtx, {
                    type: "doughnut",
                    data: {
                        labels: ["TCP", "UDP"],
                        datasets: [{ data: [tcp, udp], backgroundColor: ["#5ad8ff", "#7cf5b1"] }],
                    },
                    options: { 
                        plugins: { legend: { position: "bottom" } },
                        responsive: true,
                        maintainAspectRatio: false
                    },
                });
            } catch (err) {
                console.error("Failed to initialize connection chart:", err);
            }
        } else if (this.state.charts.connections) {
            this.state.charts.connections.data.datasets[0].data = [tcp, udp];
            this.state.charts.connections.update();
        }

        const countriesCtx = document.getElementById("countriesChart");
        if (countriesCtx && !this.state.charts.countries) {
            try {
                this.state.charts.countries = new Chart(countriesCtx, {
                    type: "bar",
                    data: {
                        labels: countries.map((c) => c[0]),
                        datasets: [{ data: countries.map((c) => c[1]), backgroundColor: "#5ad8ff" }],
                    },
                    options: { 
                        plugins: { legend: { display: false } },
                        responsive: true,
                        maintainAspectRatio: false
                    },
                });
            } catch (err) {
                console.error("Failed to initialize countries chart:", err);
            }
        } else if (this.state.charts.countries) {
            this.state.charts.countries.data.labels = countries.map((c) => c[0]);
            this.state.charts.countries.data.datasets[0].data = countries.map((c) => c[1]);
            this.state.charts.countries.update();
        }
    },

    // Patch 5: Proper event delegation for dynamic elements
    bindEvents() {
        // Static event bindings
        document.getElementById("btn-investigate")?.addEventListener("click", () => this.runInvestigation(true));
        document.getElementById("refresh-btn")?.addEventListener("click", () => this.runInvestigation(true));
        document.getElementById("btn-export-scan")?.addEventListener("click", () => this.exportInvestigation());

        // Delegated event for dynamic IP chips
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn-chip') && e.target.hasAttribute('data-ip')) {
                const ip = e.target.getAttribute('data-ip');
                if (this.el.ipInput) {
                    this.el.ipInput.value = ip;
                    this.lookupIp(ip);
                }
            }
        });

        // Other event bindings...
        document.getElementById("btn-lookup")?.addEventListener("click", () => {
            const ip = this.el.ipInput?.value.trim();
            if (ip) this.lookupIp(ip);
            else this.showToast("Enter an IP address first", "warning");
        });

        document.getElementById("my-ip-btn")?.addEventListener("click", async () => {
            try {
                const res = await this.fetchJson("/api/myip");
                if (res?.ip && this.el.ipInput) {
                    this.el.ipInput.value = res.ip;
                    this.lookupIp(res.ip);
                }
            } catch (err) {
                this.showToast("Failed to get your IP address", "danger");
            }
        });

        // Map and report events...
        document.getElementById("btn-map")?.addEventListener("click", () => this.generateMap());
        document.getElementById("btn-clear-map")?.addEventListener("click", () => this.clearMap());
        document.getElementById("btn-report")?.addEventListener("click", () => this.generateReport());
        document.getElementById("btn-download")?.addEventListener("click", () => this.downloadReport());
        document.getElementById("btn-download-pdf")?.addEventListener("click", () =>
            this.showToast("PDF export coming soon", "info")
        );

        document.getElementById("clear-history")?.addEventListener("click", () => {
            this.state.lookupHistory = [];
            try {
                localStorage.setItem("ipchecker-history", "[]");
            } catch (err) {
                console.warn("Failed to clear history:", err);
            }
            this.renderHistory();
            this.showToast("History cleared", "info");
        });
    },

    // Patch 6: Enhanced map marker cleanup
    clearMap() {
        if (this.state.markers && this.state.map) {
            try {
                this.state.markers.forEach((marker) => {
                    if (marker && typeof marker.remove === 'function') {
                        marker.remove();
                    } else if (this.state.map.hasLayer && this.state.map.removeLayer) {
                        this.state.map.removeLayer(marker);
                    }
                });
            } catch (err) {
                console.error("Error clearing map markers:", err);
            } finally {
                this.state.markers = [];
            }
        }
    },

    // Patch 7: Improved toast notifications with better positioning
    showToast(message, type = "info") {
        if (!this.el.toastContainer) {
            console.warn("Toast container not found, falling back to alert");
            alert(message);
            return;
        }
        
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        toast.textContent = message;
        
        // Ensure proper positioning
        this.el.toastContainer.style.zIndex = '9999';
        this.el.toastContainer.appendChild(toast);
        
        // Auto-remove with cleanup
        const removeToast = () => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        };
        
        setTimeout(removeToast, 4000);
        
        // Click to dismiss early
        toast.addEventListener('click', removeToast);
    },

    // Patch 8: Enhanced loading state management
    setLoading(show) {
        if (this.el.loadingOverlay) {
            this.el.loadingOverlay.style.display = show ? "flex" : "none";
            this.el.loadingOverlay.style.zIndex = '10000';
            
            // Prevent scrolling when loading
            if (show) {
                document.body.style.overflow = 'hidden';
            } else {
                document.body.style.overflow = '';
            }
        }
    }
};

// Apply patches by extending the original App object
Object.assign(window.App || {}, EnhancedApp);