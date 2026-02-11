/**
 * IP Checker Pro - HIGH PERFORMANCE OPTIMIZED VERSION
 * ================================================
 * 
 * Оптимизации:
 * - Lazy loading для всех тяжелых библиотек
 * - Дебаунсинг и троттлинг событий
 * - Виртуализация списков
 * - Кэширование DOM элементов
 * - Минимальные ре-рендеры
 * - Request batching
 */

// ============================================================================
// PERFORMANCE UTILITIES
// ============================================================================

const PerfUtils = {
    debounce(fn, delay) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn.apply(this, args), delay);
        };
    },
    
    throttle(fn, limit) {
        let inThrottle;
        return (...args) => {
            if (!inThrottle) {
                fn.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    // RAF-based throttle for animations
    rafThrottle(fn) {
        let ticking = false;
        return (...args) => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    fn.apply(this, args);
                    ticking = false;
                });
                ticking = true;
            }
        };
    },
    
    // Memoize expensive functions
    memoize(fn, ttl = 60000) {
        const cache = new Map();
        return (...args) => {
            const key = JSON.stringify(args);
            const cached = cache.get(key);
            if (cached && Date.now() - cached.time < ttl) {
                return cached.value;
            }
            const result = fn.apply(this, args);
            cache.set(key, { value: result, time: Date.now() });
            return result;
        };
    },
    
    // Batch requests to reduce API calls
    batchRequests(requests, batchSize = 5, delay = 100) {
        return new Promise((resolve) => {
            const results = [];
            let currentIndex = 0;
            
            const processBatch = () => {
                if (currentIndex >= requests.length) {
                    Promise.all(results).then(allResults => {
                        resolve(allResults.flat());
                    });
                    return;
                }
                
                const batch = requests.slice(currentIndex, currentIndex + batchSize);
                const batchPromise = Promise.all(batch.map(req => req()));
                results.push(batchPromise);
                
                currentIndex += batchSize;
                
                if (currentIndex < requests.length) {
                    setTimeout(processBatch, delay);
                } else {
                    Promise.all(results).then(allResults => {
                        resolve(allResults.flat());
                    });
                }
            };
            
            processBatch();
        });
    },
    
    // Debounced resize observer for performance
    debouncedResizeObserver(callback, delay = 250) {
        let timeoutId;
        const debouncedCallback = () => {
            window.clearTimeout(timeoutId);
            timeoutId = window.setTimeout(callback, delay);
        };
        
        return new ResizeObserver(debouncedCallback);
    }
};

// ============================================================================
// LIGHTWEIGHT NOTIFICATION SYSTEM
// ============================================================================

class LightweightNotifier {
    constructor() {
        this.container = null;
        this.notifications = [];
        this.maxNotifications = 3;
        this.init();
    }
    
    init() {
        // Create container if not exists
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 10px;
            `;
            document.body.appendChild(this.container);
        }
    }
    
    show(message, type = 'info', duration = 3000) {
        const el = document.createElement('div');
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6',
            loading: '#8b5cf6'
        };
        
        el.style.cssText = `
            background: ${colors[type] || colors.info};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 200px;
            animation: slideIn 0.3s ease;
        `;
        
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ',
            loading: '⟳'
        };
        
        el.innerHTML = `
            <span style="font-size: 16px;">${icons[type] || icons.info}</span>
            <span>${message}</span>
        `;
        
        // Remove oldest if at max
        if (this.notifications.length >= this.maxNotifications) {
            this.notifications[0].remove();
            this.notifications.shift();
        }
        
        this.container.appendChild(el);
        this.notifications.push(el);
        
        // Auto remove
        if (duration > 0) {
            setTimeout(() => this.remove(el), duration);
        }
        
        return {
            element: el,
            dismiss: () => this.remove(el)
        };
    }
    
    remove(el) {
        if (!el || el.removing) return;
        el.removing = true;
        el.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => {
            el.remove();
            this.notifications = this.notifications.filter(n => n !== el);
        }, 300);
    }
    
    success(msg, opts) { return this.show(msg, 'success', opts?.duration || 3000); }
    error(msg, opts) { return this.show(msg, 'error', opts?.duration || 5000); }
    warning(msg, opts) { return this.show(msg, 'warning', opts?.duration || 4000); }
    info(msg, opts) { return this.show(msg, 'info', opts?.duration || 3000); }
    loading(msg) { return this.show(msg || 'Loading...', 'loading', 0); }
}

// Global notifier instance
const notifier = new LightweightNotifier();
window.notyf = notifier; // Compatibility

// ============================================================================
// MAIN APPLICATION
// ============================================================================

const App = {
    state: {
        investigation: null,
        charts: {},
        map: null,
        markerCluster: null,
        connectionsTable: null,
        lookupHistory: [],
        lastReport: null,
        isLoading: false,
        initialized: {
            charts: false,
            table: false,
            map: false
        },
        dataCache: new Map()
    },
    
    // Cached DOM elements
    el: {},
    
    init() {
        this.loadHistory();
        this.cacheDom();
        this.bindEvents();
        this.runInvestigation();
    },
    
    cacheDom() {
        // Cache frequently accessed elements
        this.el = {
            dashboardSkeleton: document.getElementById("dashboard-skeleton"),
            dashboardContent: document.getElementById("dashboard-content"),
            activeConnections: document.getElementById("active-connections"),
            secureConnections: document.getElementById("secure-connections"),
            warningsCount: document.getElementById("warnings-count"),
            threatsCount: document.getElementById("threats-count"),
            connectionChart: document.getElementById("connectionChart"),
            countriesChart: document.getElementById("countriesChart"),
            connectionsTable: document.getElementById("connections-table"),
            sysHostname: document.getElementById("sys-hostname"),
            sysPlatform: document.getElementById("sys-platform"),
            sysTime: document.getElementById("sys-time"),
            sysInterfaces: document.getElementById("sys-interfaces"),
            interfacesList: document.getElementById("interfaces-list"),
            scanProgress: document.getElementById("scan-progress"),
            progressFill: document.querySelector(".progress-fill"),
            loadingOverlay: document.getElementById("loading-overlay"),
            ipInput: document.getElementById("ip-input"),
            lookupResults: document.getElementById("lookup-results"),
            lookupEmpty: document.getElementById("lookup-empty"),
            recentIps: document.getElementById("recent-ips"),
            miniMap: document.getElementById("mini-map"),
            mapTextarea: document.getElementById("ips-input"),
            securityScore: document.querySelector("#security-score .score-value"),
            securityList: document.getElementById("security-list"),
            includeSystem: document.getElementById("include-system"),
            includeConnections: document.getElementById("include-connections"),
            includeSecurity: document.getElementById("include-security"),
            includeGeolocation: document.getElementById("include-geolocation"),
            reportResults: document.getElementById("report-results"),
            exportButtons: document.getElementById("export-buttons"),
            historyList: document.getElementById("history-list"),
            criticalThreats: document.getElementById("critical-threats"),
            highWarnings: document.getElementById("high-warnings"),
            secureConnectionsNew: document.getElementById("secure-connections"),
            totalConnections: document.getElementById("total-connections"),
            securityScoreDisplay: document.querySelector(".security-score-number"),
            securityStatusHeader: document.getElementById("security-status-header"),
        };
    },
    
    bindEvents() {
        // Scan buttons
        document.getElementById("btn-investigate")?.addEventListener("click", () => this.runInvestigation(true));
        document.getElementById("refresh-btn")?.addEventListener("click", PerfUtils.debounce(() => this.runInvestigation(true), 500));
        document.getElementById("btn-export-scan")?.addEventListener("click", () => this.exportInvestigation());
        
        // Lookup
        document.getElementById("btn-lookup")?.addEventListener("click", () => {
            const ip = this.el.ipInput?.value.trim();
            if (ip) this.lookupIp(ip);
            else notifier.warning("Enter an IP address");
        });
        
        // Quick lookup chips
        document.querySelectorAll(".btn-chip[data-ip]").forEach(btn => {
            btn.addEventListener("click", () => {
                const ip = btn.getAttribute("data-ip");
                if (this.el.ipInput) this.el.ipInput.value = ip;
                this.lookupIp(ip);
            });
        });
        
        // My IP
        document.getElementById("my-ip-btn")?.addEventListener("click", async () => {
            const res = await this.fetchJson("/api/myip");
            if (res?.ip && this.el.ipInput) {
                this.el.ipInput.value = res.ip;
                this.lookupIp(res.ip);
            }
        });
        
        // Map
        document.getElementById("btn-map")?.addEventListener("click", () => this.generateMap());
        document.getElementById("btn-clear-map")?.addEventListener("click", () => this.clearMap());
        
        // Report
        document.getElementById("btn-report")?.addEventListener("click", () => this.generateReport());
        document.getElementById("btn-download")?.addEventListener("click", () => this.downloadReport());
        
        // History
        document.getElementById("clear-history")?.addEventListener("click", () => {
            this.state.lookupHistory = [];
            localStorage.setItem("ipchecker-history", "[]");
            this.renderHistory();
            notifier.success("History cleared");
        });
        
        // IP input Enter key
        this.el.ipInput?.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                const ip = this.el.ipInput?.value.trim();
                if (ip) this.lookupIp(ip);
            }
        });
        
        // Tab switching with lazy init
        document.querySelectorAll('.nav-item').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabId = tab.getAttribute('data-tab');
                this.onTabChange(tabId);
            });
        });
    },
    
    async onTabChange(tabId) {
        // Lazy load resources based on tab
        switch(tabId) {
            case 'dashboard':
                if (!this.state.initialized.charts) {
                    await window.loadApexCharts();
                    this.initCharts();
                    this.state.initialized.charts = true;
                }
                break;
            case 'investigate':
                if (!this.state.initialized.table) {
                    await window.loadTabulator();
                    this.initConnectionsTable();
                    this.state.initialized.table = true;
                }
                break;
            case 'map':
            case 'lookup':
                if (!this.state.initialized.map) {
                    await window.loadLeaflet();
                    this.initMap();
                    this.state.initialized.map = true;
                }
                break;
        }
    },
    
    // ============================================================================
    // DATA FETCHING
    // ============================================================================
    
    async fetchJson(url, options = {}) {
        const startTime = performance.now();
        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Accept': 'application/json',
                    ...options.headers
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            // Log slow requests in debug mode
            const duration = performance.now() - startTime;
            if (duration > 1000) {
                console.warn(`[Perf] Slow request: ${url} took ${duration.toFixed(0)}ms`);
            }
            
            return data;
        } catch (error) {
            console.error(`[Error] Fetch failed: ${url}`, error);
            throw error;
        }
    },
    
    // ============================================================================
    // INVESTIGATION
    // ============================================================================
    
    async runInvestigation(showLoading = false) {
        if (this.state.isLoading) return;
        
        this.state.isLoading = true;
        const loadingId = showLoading ? notifier.loading("Scanning system...") : null;
        
        try {
            const data = await this.fetchJson("/api/investigate");
            this.state.investigation = data;
            
            this.updateDashboard(data);
            this.updateSystemInfo(data);
            this.updateConnectionsTable(data.connections);
            
            notifier.success("Scan completed");
        } catch (error) {
            notifier.error("Scan failed: " + error.message);
        } finally {
            this.state.isLoading = false;
            if (loadingId) loadingId.dismiss();
        }
    },
    
    updateDashboard(data) {
        const security = data.security || {};
        
        // Update metric cards
        if (this.el.criticalThreats) this.el.criticalThreats.textContent = security.threats || 0;
        if (this.el.highWarnings) this.el.highWarnings.textContent = security.warnings || 0;
        if (this.el.secureConnectionsNew) this.el.secureConnectionsNew.textContent = security.secure || 0;
        if (this.el.totalConnections) this.el.totalConnections.textContent = security.total_connections || 0;
        
        // Update security score
        if (this.el.securityScoreDisplay) {
            this.el.securityScoreDisplay.innerHTML = `${security.score || 0}<span class="text-2xl">/100</span>`;
        }
        
        // Update charts if initialized
        if (this.state.initialized.charts) {
            this.updateCharts(data);
        }
        
        // Hide skeleton
        if (this.el.dashboardSkeleton) {
            this.el.dashboardSkeleton.style.display = 'none';
        }
    },
    
    updateSystemInfo(data) {
        if (this.el.sysHostname) this.el.sysHostname.textContent = data.hostname || '-';
        if (this.el.sysPlatform) this.el.sysPlatform.textContent = data.platform || '-';
        if (this.el.sysTime) this.el.sysTime.textContent = new Date().toLocaleString();
        if (this.el.sysInterfaces) this.el.sysInterfaces.textContent = data.interfaces?.length || 0;
        
        // Update interfaces list
        if (this.el.interfacesList && data.interfaces) {
            this.el.interfacesList.innerHTML = data.interfaces.map(iface => `
                <div class="interface-item">
                    <span class="interface-name">${iface.name}</span>
                    <span class="interface-ips">${iface.addresses.map(a => a.address).join(', ')}</span>
                </div>
            `).join('');
        }
    },
    
    // ============================================================================
    // CHARTS
    // ============================================================================
    
    async initCharts() {
        if (!window.ApexCharts) return;
        
        // Connection types chart
        if (this.el.connectionChart) {
            this.state.charts.connections = new ApexCharts(this.el.connectionChart, {
                chart: { type: 'donut', height: 300, fontFamily: 'inherit' },
                series: [0, 0],
                labels: ['TCP', 'UDP'],
                colors: ['#3b82f6', '#10b981'],
                legend: { position: 'bottom' },
                plotOptions: {
                    pie: {
                        donut: {
                            size: '70%',
                            labels: {
                                show: true,
                                total: { show: true, label: 'Total' }
                            }
                        }
                    }
                }
            });
            this.state.charts.connections.render();
        }
        
        // Countries chart
        if (this.el.countriesChart) {
            this.state.charts.countries = new ApexCharts(this.el.countriesChart, {
                chart: { type: 'bar', height: 300, fontFamily: 'inherit' },
                series: [{ name: 'Connections', data: [] }],
                xaxis: { categories: [] },
                colors: ['#8b5cf6'],
                plotOptions: {
                    bar: { borderRadius: 4, horizontal: true }
                }
            });
            this.state.charts.countries.render();
        }
    },
    
    updateCharts(data) {
        const connections = data.connections || [];
        const summary = data.summary || {};
        
        // Update connection types
        const tcp = connections.filter(c => c.protocol === 'TCP').length;
        const udp = connections.filter(c => c.protocol === 'UDP').length;
        
        if (this.state.charts.connections) {
            this.state.charts.connections.updateSeries([tcp, udp]);
        }
        
        // Update countries
        const countries = summary.top_countries || [];
        if (this.state.charts.countries && countries.length > 0) {
            this.state.charts.countries.updateOptions({
                xaxis: { categories: countries.map(c => c[0]) }
            });
            this.state.charts.countries.updateSeries([{
                name: 'Connections',
                data: countries.map(c => c[1])
            }]);
        }
    },
    
    // ============================================================================
    // CONNECTIONS TABLE
    // ============================================================================
    
    async initConnectionsTable() {
        if (!window.Tabulator) return;
        
        this.state.connectionsTable = new Tabulator(this.el.connectionsTable, {
            layout: "fitColumns",
            pagination: true,
            paginationSize: 25,
            paginationSizeSelector: [25, 50, 100],
            movableColumns: true,
            columns: [
                { title: "Process", field: "process", width: 120 },
                { title: "Remote", field: "remote_addr", width: 150 },
                { title: "Status", field: "status", width: 100 },
                { title: "Protocol", field: "protocol", width: 80 },
                { title: "Country", field: "geo.country", width: 100 },
                { title: "Risk", field: "risk_level", width: 80, formatter: "traffic" }
            ],
            rowFormatter: (row) => {
                const data = row.getData();
                if (data.risk_level === 'danger') {
                    row.getElement().style.background = "rgba(239, 68, 68, 0.1)";
                } else if (data.risk_level === 'warning') {
                    row.getElement().style.background = "rgba(245, 158, 11, 0.1)";
                }
            }
        });
    },
    
    updateConnectionsTable(connections) {
        if (this.state.connectionsTable) {
            this.state.connectionsTable.setData(connections || []);
        }
        
        // Update security list
        if (this.el.securityList) {
            const findings = (connections || [])
                .filter(c => c.risk_level !== 'info')
                .slice(0, 30);
            
            if (findings.length === 0) {
                this.el.securityList.innerHTML = `
                    <div class="finding-item info">
                        <i class="fas fa-check-circle"></i>
                        <div class="finding-content"><h4>No threats found</h4><p>Your system looks secure</p></div>
                    </div>
                `;
            } else {
                this.el.securityList.innerHTML = findings.map(f => `
                    <div class="finding-item ${f.risk_level}">
                        <i class="fas fa-${f.risk_level === 'danger' ? 'fire' : 'exclamation-triangle'}"></i>
                        <div class="finding-content">
                            <h4>${f.remote_addr}</h4>
                            <p>${f.process} - ${f.risks.join(', ')}</p>
                        </div>
                    </div>
                `).join('');
            }
        }
    },
    
    // ============================================================================
    // IP LOOKUP
    // ============================================================================
    
    async lookupIp(ip) {
        if (!ip || !this.isValidIp(ip)) {
            notifier.warning("Invalid IP address");
            return;
        }
        
        const loading = notifier.loading(`Looking up ${ip}...`);
        
        try {
            const data = await this.fetchJson(`/api/lookup?ip=${encodeURIComponent(ip)}`);
            this.displayLookupResults(data);
            this.addToHistory(ip, data.geolocation);
            notifier.success("Lookup complete");
        } catch (error) {
            notifier.error("Lookup failed");
        } finally {
            loading.dismiss();
        }
    },
    
    displayLookupResults(data) {
        const geo = data.geolocation || {};
        
        // Show results panel
        if (this.el.lookupEmpty) this.el.lookupEmpty.style.display = 'none';
        if (this.el.lookupResults) this.el.lookupResults.style.display = 'block';
        
        // Update fields
        const fields = {
            'result-ip': data.ip,
            'result-country': geo.country,
            'result-region': geo.region,
            'result-city': geo.city,
            'result-zip': geo.zip || geo.postal,
            'result-coords': (geo.lat && geo.lon) ? `${geo.lat}, ${geo.lon}` : '-',
            'result-timezone': geo.timezone,
            'result-isp': geo.isp,
            'result-org': geo.org,
            'result-asn': geo.asn,
            'result-hostname': data.reverse_dns?.hostname || '-'
        };
        
        Object.entries(fields).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value || '-';
        });
        
        // Update mini map
        if (geo.lat && geo.lon && window.L) {
            this.updateMiniMap(geo.lat, geo.lon, data.ip);
        }
    },
    
    // ============================================================================
    // MAP
    // ============================================================================
    
    async initMap() {
        if (!window.L) return;
        
        // Main map
        const mapContainer = document.getElementById('map-container');
        if (mapContainer) {
            this.state.map = L.map('map-container').setView([20, 0], 2);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap',
                maxZoom: 18
            }).addTo(this.state.map);
            
            this.state.markerCluster = L.markerClusterGroup();
            this.state.map.addLayer(this.state.markerCluster);
        }
        
        // Mini map for lookup
        if (this.el.miniMap && !this.state.miniMap) {
            this.state.miniMap = L.map('mini-map', { zoomControl: false }).setView([0, 0], 2);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '',
                maxZoom: 18
            }).addTo(this.state.miniMap);
        }
    },
    
    updateMiniMap(lat, lon, ip) {
        if (!this.state.miniMap) return;
        
        this.state.miniMap.setView([lat, lon], 10);
        
        // Clear existing markers
        this.state.miniMap.eachLayer(layer => {
            if (layer instanceof L.Marker) layer.remove();
        });
        
        L.marker([lat, lon]).addTo(this.state.miniMap).bindPopup(ip);
    },
    
    async generateMap() {
        const ips = this.el.mapTextarea?.value.split('\n').filter(ip => ip.trim());
        
        if (!ips || ips.length === 0) {
            notifier.warning("Enter at least one IP address");
            return;
        }
        
        if (!window.L) {
            await window.loadLeaflet();
            await this.initMap();
        }
        
        const loading = notifier.loading(`Looking up ${ips.length} IPs...`);
        
        try {
            const response = await fetch('/api/map', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ips })
            });
            
            const data = await response.json();
            
            if (data.locations) {
                this.state.markerCluster.clearLayers();
                
                data.locations.forEach(loc => {
                    if (loc.lat && loc.lon) {
                        const marker = L.marker([loc.lat, loc.lon])
                            .bindPopup(`${loc.ip}<br>${loc.city}, ${loc.country}`);
                        this.state.markerCluster.addLayer(marker);
                    }
                });
                
                if (data.locations.length > 0) {
                    const group = new L.featureGroup(this.state.markerCluster.getLayers());
                    this.state.map.fitBounds(group.getBounds().pad(0.1));
                }
                
                notifier.success(`Mapped ${data.locations.length} locations`);
            }
        } catch (error) {
            notifier.error("Map generation failed");
        } finally {
            loading.dismiss();
        }
    },
    
    clearMap() {
        if (this.state.markerCluster) {
            this.state.markerCluster.clearLayers();
        }
        if (this.el.mapTextarea) {
            this.el.mapTextarea.value = '';
        }
    },
    
    // ============================================================================
    // REPORTS
    // ============================================================================
    
    async generateReport() {
        const params = new URLSearchParams({
            include_system: this.el.includeSystem?.checked || false,
            include_connections: this.el.includeConnections?.checked || false,
            include_security: this.el.includeSecurity?.checked || false,
            include_geolocation: this.el.includeGeolocation?.checked || false,
        });
        
        const loading = notifier.loading("Generating report...");
        
        try {
            const data = await this.fetchJson(`/api/report?${params}`);
            this.state.lastReport = data;
            
            if (this.el.reportResults) {
                this.el.reportResults.innerHTML = `<pre class="report-json">${JSON.stringify(data, null, 2)}</pre>`;
            }
            
            if (this.el.exportButtons) {
                this.el.exportButtons.style.display = 'flex';
            }
            
            notifier.success("Report generated");
        } catch (error) {
            notifier.error("Report generation failed");
        } finally {
            loading.dismiss();
        }
    },
    
    downloadReport() {
        if (!this.state.lastReport) return;
        
        const blob = new Blob([JSON.stringify(this.state.lastReport, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ip-checker-report-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    },
    
    // ============================================================================
    // HISTORY
    // ============================================================================
    
    loadHistory() {
        try {
            const stored = localStorage.getItem("ipchecker-history");
            this.state.lookupHistory = stored ? JSON.parse(stored) : [];
            this.renderHistory();
        } catch (e) {
            this.state.lookupHistory = [];
        }
    },
    
    addToHistory(ip, geo) {
        const entry = {
            ip,
            country: geo?.country,
            city: geo?.city,
            timestamp: Date.now()
        };
        
        // Remove duplicates
        this.state.lookupHistory = this.state.lookupHistory.filter(h => h.ip !== ip);
        this.state.lookupHistory.unshift(entry);
        
        // Keep only last 20
        if (this.state.lookupHistory.length > 20) {
            this.state.lookupHistory = this.state.lookupHistory.slice(0, 20);
        }
        
        localStorage.setItem("ipchecker-history", JSON.stringify(this.state.lookupHistory));
        this.renderHistory();
    },
    
    renderHistory() {
        if (!this.el.historyList) return;
        
        if (this.state.lookupHistory.length === 0) {
            this.el.historyList.innerHTML = '<div class="empty-state"><i class="fas fa-history"></i><p>No history yet</p></div>';
            return;
        }
        
        this.el.historyList.innerHTML = this.state.lookupHistory.map(h => `
            <div class="history-item" data-ip="${h.ip}">
                <div class="history-ip">${h.ip}</div>
                <div class="history-location">${h.city || ''}, ${h.country || ''}</div>
                <div class="history-time">${new Date(h.timestamp).toLocaleDateString()}</div>
            </div>
        `).join('');
        
        // Add click handlers
        this.el.historyList.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', () => {
                const ip = item.getAttribute('data-ip');
                if (this.el.ipInput) this.el.ipInput.value = ip;
                this.lookupIp(ip);
                
                // Switch to lookup tab
                document.querySelector('[data-tab="lookup"]')?.click();
            });
        });
    },
    
    // ============================================================================
    // UTILITIES
    // ============================================================================
    
    isValidIp(ip) {
        const ipv4 = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        const ipv6 = /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/;
        return ipv4.test(ip) || ipv6.test(ip);
    },
    
    exportInvestigation() {
        if (!this.state.investigation) return;
        
        const blob = new Blob([JSON.stringify(this.state.investigation, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `investigation-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => App.init());
window.App = App;

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
