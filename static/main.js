/* Enhanced IP Checker Pro - Main Application Logic */

// Enhanced Notyf Notification System
const notyf = new Notyf({
    duration: 4000,
    position: { x: 'right', y: 'top' },
    dismissible: true,
    ripple: true,
    types: [
        {
            type: 'success',
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            icon: {
                className: 'fas fa-check-circle',
                tagName: 'i',
                color: '#ffffff'
            },
            className: 'notyf-success',
            duration: 3000
        },
        {
            type: 'error',
            background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
            icon: {
                className: 'fas fa-exclamation-circle',
                tagName: 'i',
                color: '#ffffff'
            },
            className: 'notyf-error',
            duration: 5000
        },
        {
            type: 'warning',
            background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            icon: {
                className: 'fas fa-exclamation-triangle',
                tagName: 'i',
                color: '#ffffff'
            },
            className: 'notyf-warning',
            duration: 4000
        },
        {
            type: 'info',
            background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
            icon: {
                className: 'fas fa-info-circle',
                tagName: 'i',
                color: '#ffffff'
            },
            className: 'notyf-info',
            duration: 4000
        },
        {
            type: 'loading',
            background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
            icon: {
                className: 'fas fa-spinner fa-spin',
                tagName: 'i',
                color: '#ffffff'
            },
            className: 'notyf-loading',
            duration: 0 // Persistent until manually dismissed
        }
    ]
});

// Enhanced Notification Manager
class NotificationManager {
    constructor(notyfInstance) {
        this.notyf = notyfInstance;
        this.notificationHistory = [];
        this.maxHistory = 50;
        this.soundEnabled = localStorage.getItem('notificationsSound') !== 'false';
        this.vibrationEnabled = localStorage.getItem('notificationsVibration') !== 'false';
        
        // Initialize enhanced features
        this.initNotificationCenter();
        this.initSoundEffects();
        this.initPersistence();
    }
    
    // Enhanced notification methods
    success(message, options = {}) {
        return this.showNotification('success', message, options);
    }
    
    error(message, options = {}) {
        return this.showNotification('error', message, options);
    }
    
    warning(message, options = {}) {
        return this.showNotification('warning', message, options);
    }
    
    info(message, options = {}) {
        return this.showNotification('info', message, options);
    }
    
    loading(message = 'Loading...', options = {}) {
        return this.showNotification('loading', message, options);
    }
    
    showNotification(type, message, options = {}) {
        const defaultOptions = {
            message: message,
            type: type,
            duration: this.getDefaultDuration(type),
            dismissible: true,
            ripple: true,
            ...options
        };
        
        // Add timestamp and metadata
        const notificationData = {
            id: Date.now() + Math.random(),
            type: type,
            message: message,
            timestamp: new Date(),
            options: defaultOptions,
            read: false
        };
        
        // Show notification
        const notification = this.notyf.open(defaultOptions);
        
        // Store in history
        this.addToHistory(notificationData);
        
        // Trigger side effects
        this.playSound(type);
        this.triggerVibration(type);
        this.sendToNotificationCenter(notificationData);
        
        return {
            notification: notification,
            id: notificationData.id,
            dismiss: () => this.dismissNotification(notificationData.id)
        };
    }
    
    getDefaultDuration(type) {
        const durations = {
            success: 3000,
            error: 5000,
            warning: 4000,
            info: 4000,
            loading: 0
        };
        return durations[type] || 4000;
    }
    
    addToHistory(notificationData) {
        this.notificationHistory.unshift(notificationData);
        
        // Limit history size
        if (this.notificationHistory.length > this.maxHistory) {
            this.notificationHistory = this.notificationHistory.slice(0, this.maxHistory);
        }
        
        // Persist to localStorage
        this.persistHistory();
    }
    
    persistHistory() {
        try {
            const serializableHistory = this.notificationHistory.map(item => ({
                ...item,
                timestamp: item.timestamp.toISOString()
            }));
            localStorage.setItem('notificationHistory', JSON.stringify(serializableHistory));
        } catch (e) {
            console.warn('Failed to persist notification history:', e);
        }
    }
    
    loadHistory() {
        try {
            const stored = localStorage.getItem('notificationHistory');
            if (stored) {
                const parsed = JSON.parse(stored);
                this.notificationHistory = parsed.map(item => ({
                    ...item,
                    timestamp: new Date(item.timestamp)
                }));
            }
        } catch (e) {
            console.warn('Failed to load notification history:', e);
        }
    }
    
    initPersistence() {
        this.loadHistory();
        
        // Auto-clean old notifications
        setInterval(() => {
            const cutoff = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000); // 1 week ago
            this.notificationHistory = this.notificationHistory.filter(
                item => item.timestamp > cutoff
            );
            this.persistHistory();
        }, 60 * 60 * 1000); // Run every hour
    }
    
    initSoundEffects() {
        // Create audio context for sound effects
        this.audioContext = null;
        this.sounds = {};
        
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.createSounds();
        } catch (e) {
            console.warn('Web Audio API not supported:', e);
        }
    }
    
    createSounds() {
        // Create simple beep sounds for different notification types
        this.sounds = {
            success: () => this.createBeep(523.25, 0.1), // C5
            error: () => this.createBeep(261.63, 0.3),   // C4
            warning: () => this.createBeep(349.23, 0.2), // F4
            info: () => this.createBeep(440, 0.15)       // A4
        };
    }
    
    createBeep(frequency, duration) {
        if (!this.audioContext || !this.soundEnabled) return;
        
        try {
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            oscillator.frequency.value = frequency;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.1, this.audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);
            
            oscillator.start(this.audioContext.currentTime);
            oscillator.stop(this.audioContext.currentTime + duration);
        } catch (e) {
            console.warn('Failed to play sound:', e);
        }
    }
    
    playSound(type) {
        if (this.sounds[type] && this.soundEnabled) {
            this.sounds[type]();
        }
    }
    
    triggerVibration(type) {
        if (!this.vibrationEnabled || !navigator.vibrate) return;
        
        const patterns = {
            success: [100],
            error: [200, 100, 200],
            warning: [300],
            info: [100, 50, 100]
        };
        
        const pattern = patterns[type] || [100];
        navigator.vibrate(pattern);
    }
    
    initNotificationCenter() {
        // Create notification center button
        this.createNotificationCenterButton();
        
        // Listen for notification events
        document.addEventListener('notyf', (e) => {
            if (e.detail.type === 'dismiss') {
                this.markAsRead(e.detail.id);
            }
        });
    }
    
    createNotificationCenterButton() {
        const button = document.createElement('button');
        button.className = 'btn-icon btn-ghost notification-center-btn';
        button.innerHTML = '<i class="fas fa-bell"></i>';
        button.setAttribute('aria-label', 'Notification Center');
        button.addEventListener('click', () => this.toggleNotificationCenter());
        
        // Add badge for unread notifications
        const badge = document.createElement('span');
        badge.className = 'notification-badge';
        badge.style.cssText = `
            position: absolute;
            top: -5px;
            right: -5px;
            background: var(--danger);
            color: white;
            border-radius: 50%;
            width: 18px;
            height: 18px;
            font-size: 10px;
            display: none;
            align-items: center;
            justify-content: center;
        `;
        button.style.position = 'relative';
        button.appendChild(badge);
        
        // Update badge count
        this.updateBadgeCount = () => {
            const unreadCount = this.notificationHistory.filter(n => !n.read).length;
            if (unreadCount > 0) {
                badge.textContent = unreadCount > 9 ? '9+' : unreadCount;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        };
        
        // Add to header
        const headerActions = document.querySelector('.header-actions');
        if (headerActions) {
            headerActions.appendChild(button);
        }
    }
    
    toggleNotificationCenter() {
        if (this.notificationCenterOpen) {
            this.closeNotificationCenter();
        } else {
            this.openNotificationCenter();
        }
    }
    
    openNotificationCenter() {
        this.notificationCenterOpen = true;
        
        const modal = document.createElement('div');
        modal.className = 'notification-center-modal';
        modal.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                right: 0;
                width: 400px;
                height: 100vh;
                background: var(--panel);
                border-left: 1px solid var(--border);
                box-shadow: -5px 0 15px rgba(0,0,0,0.3);
                z-index: 10000;
                display: flex;
                flex-direction: column;
            ">
                <div style="
                    padding: 1rem;
                    border-bottom: 1px solid var(--border);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <h3 style="margin: 0; color: var(--text);">Notifications</h3>
                    <button class="btn-icon btn-ghost" onclick="this.closest('.notification-center-modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div style="
                    flex: 1;
                    overflow-y: auto;
                    padding: 1rem;
                " class="notification-list">
                    ${this.renderNotificationList()}
                </div>
                <div style="
                    padding: 1rem;
                    border-top: 1px solid var(--border);
                    display: flex;
                    gap: 0.5rem;
                ">
                    <button class="btn btn-secondary btn-sm" onclick="notificationManager.markAllAsRead()">
                        Mark All Read
                    </button>
                    <button class="btn btn-outline btn-sm" onclick="notificationManager.clearAll()">
                        Clear All
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeNotificationCenter();
            }
        });
        
        // Mark as read when opened
        this.markAllAsRead();
        this.updateBadgeCount();
    }
    
    closeNotificationCenter() {
        this.notificationCenterOpen = false;
        const modal = document.querySelector('.notification-center-modal');
        if (modal) {
            modal.remove();
        }
    }
    
    renderNotificationList() {
        if (this.notificationHistory.length === 0) {
            return `
                <div style="
                    text-align: center;
                    padding: 2rem;
                    color: var(--text-muted);
                ">
                    <i class="fas fa-bell-slash" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p>No notifications yet</p>
                </div>
            `;
        }
        
        return this.notificationHistory.map(notification => `
            <div style="
                padding: 1rem;
                border-radius: var(--radius);
                margin-bottom: 0.5rem;
                background: ${notification.read ? 'var(--bg-secondary)' : 'var(--panel-strong)'};
                border: 1px solid var(--border);
                transition: all 0.2s ease;
            " class="notification-item" data-id="${notification.id}">
                <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
                    <div style="
                        width: 24px;
                        height: 24px;
                        border-radius: 50%;
                        background: ${this.getNotificationColor(notification.type)};
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        flex-shrink: 0;
                    ">
                        <i class="${this.getNotificationIcon(notification.type)}" style="color: white; font-size: 12px;"></i>
                    </div>
                    <div style="flex: 1; min-width: 0;">
                        <p style="
                            margin: 0 0 0.25rem 0;
                            color: var(--text);
                            font-size: 0.875rem;
                            line-height: 1.4;
                        ">\n${notification.message}</p>
                        <p style="
                            margin: 0;
                            color: var(--text-muted);
                            font-size: 0.75rem;
                        ">\n${this.formatTimestamp(notification.timestamp)}</p>
                    </div>
                    <button class="btn-icon btn-ghost btn-sm" onclick="notificationManager.dismissNotification('${notification.id}')" style="flex-shrink: 0;">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    getNotificationColor(type) {
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6',
            loading: '#8b5cf6'
        };
        return colors[type] || '#64748b';
    }
    
    getNotificationIcon(type) {
        const icons = {
            success: 'fas fa-check',
            error: 'fas fa-exclamation',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info',
            loading: 'fas fa-spinner'
        };
        return icons[type] || 'fas fa-bell';
    }
    
    formatTimestamp(date) {
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString();
    }
    
    sendToNotificationCenter(notificationData) {
        // Update notification center if open
        if (this.notificationCenterOpen) {
            const list = document.querySelector('.notification-list');
            if (list) {
                list.innerHTML = this.renderNotificationList();
            }
        }
        
        // Update badge
        this.updateBadgeCount();
    }
    
    markAsRead(id) {
        const notification = this.notificationHistory.find(n => n.id == id);
        if (notification) {
            notification.read = true;
            this.persistHistory();
            this.updateBadgeCount();
        }
    }
    
    markAllAsRead() {
        this.notificationHistory.forEach(notification => {
            notification.read = true;
        });
        this.persistHistory();
        this.updateBadgeCount();
        
        if (this.notificationCenterOpen) {
            const list = document.querySelector('.notification-list');
            if (list) {
                list.innerHTML = this.renderNotificationList();
            }
        }
    }
    
    dismissNotification(id) {
        this.notificationHistory = this.notificationHistory.filter(n => n.id != id);
        this.persistHistory();
        this.updateBadgeCount();
        
        if (this.notificationCenterOpen) {
            const item = document.querySelector(`[data-id="${id}"]`);
            if (item) {
                item.style.opacity = '0';
                item.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    item.remove();
                    // Refresh if list is empty
                    if (this.notificationHistory.length === 0) {
                        const list = document.querySelector('.notification-list');
                        if (list) {
                            list.innerHTML = this.renderNotificationList();
                        }
                    }
                }, 200);
            }
        }
    }
    
    clearAll() {
        this.notificationHistory = [];
        this.persistHistory();
        this.updateBadgeCount();
        
        if (this.notificationCenterOpen) {
            const list = document.querySelector('.notification-list');
            if (list) {
                list.innerHTML = this.renderNotificationList();
            }
        }
    }
    
    // Settings methods
    setSoundEnabled(enabled) {
        this.soundEnabled = enabled;
        localStorage.setItem('notificationsSound', enabled);
    }
    
    setVibrationEnabled(enabled) {
        this.vibrationEnabled = enabled;
        localStorage.setItem('notificationsVibration', enabled);
    }
    
    getUnreadCount() {
        return this.notificationHistory.filter(n => !n.read).length;
    }
    
    getRecentNotifications(limit = 10) {
        return this.notificationHistory.slice(0, limit);
    }
}

// Initialize enhanced notification manager
const notificationManager = new NotificationManager(notyf);

// Replace global notyf with enhanced version
window.notyf = {
    success: (message, options) => notificationManager.success(message, options),
    error: (message, options) => notificationManager.error(message, options),
    warning: (message, options) => notificationManager.warning(message, options),
    info: (message, options) => notificationManager.info(message, options),
    loading: (message, options) => notificationManager.loading(message, options),
    dismiss: (id) => notificationManager.dismissNotification(id)
};

const App = {
    state: {
        investigation: null,
        charts: { connections: null, countries: null },
        map: null,
        markerCluster: null,
        connectionsTable: null,
        lookupHistory: [],
        lastReport: null,
        isLoading: false,
        securityTimeline: [],
        securitySnapshot: null,
        mapInitialized: false,
        tableInitialized: false,
        chartsInitialized: false,
    },

    init() {
        this.state.lookupHistory = this.safeLoadHistory();
        this.cacheDom();
        this.bindEvents();
        // Heavy components are lazy-initialized per tab
        this.lazyInitTab("dashboard");
        this.initKeyboardNavigation();
        this.initFormValidation();
        this.renderHistory();
        
        // Run initial investigation with skeleton loading
        this.showDashboardSkeleton();
        this.runInvestigation();
        
        // GSAP entrance animations
        this.animateEntrance();
    },

    cacheDom() {
        this.el = {
            // Dashboard elements
            dashboardSkeleton: document.getElementById("dashboard-skeleton"),
            dashboardContent: document.getElementById("dashboard-content"),
            activeConnections: document.getElementById("active-connections"),
            secureConnections: document.getElementById("secure-connections"),
            warningsCount: document.getElementById("warnings-count"),
            threatsCount: document.getElementById("threats-count"),
            
            // Charts
            connectionChart: document.getElementById("connectionChart"),
            countriesChart: document.getElementById("countriesChart"),
            
            // Tables
            connectionsTable: document.getElementById("connections-table"),
            
            // System info
            sysHostname: document.getElementById("sys-hostname"),
            sysPlatform: document.getElementById("sys-platform"),
            sysTime: document.getElementById("sys-time"),
            sysInterfaces: document.getElementById("sys-interfaces"),
            interfacesList: document.getElementById("interfaces-list"),
            activityList: document.getElementById("activity-list"),
            
            // Progress
            scanProgress: document.getElementById("scan-progress"),
            progressFill: document.querySelector(".progress-fill"),
            
            // Loading
            loadingOverlay: document.getElementById("loading-overlay"),
            
            // IP Lookup
            ipInput: document.getElementById("ip-input"),
            lookupResults: document.getElementById("lookup-results"),
            lookupEmpty: document.getElementById("lookup-empty"),
            recentIps: document.getElementById("recent-ips"),
            
            // Result fields
            resultFields: {
                ip: document.getElementById("result-ip"),
                flag: document.getElementById("result-flag"),
                country: document.getElementById("result-country"),
                region: document.getElementById("result-region"),
                city: document.getElementById("result-city"),
                zip: document.getElementById("result-zip"),
                coords: document.getElementById("result-coords"),
                timezone: document.getElementById("result-timezone"),
                isp: document.getElementById("result-isp"),
                org: document.getElementById("result-org"),
                asn: document.getElementById("result-asn"),
                hostname: document.getElementById("result-hostname"),
            },
            
            // Map
            miniMap: document.getElementById("mini-map"),
            mapTextarea: document.getElementById("ips-input"),
            
            // Security
            securityScore: document.querySelector("#security-score .score-value"),
            securityList: document.getElementById("security-list"),
            
            // Report
            includeSystem: document.getElementById("include-system"),
            includeConnections: document.getElementById("include-connections"),
            includeSecurity: document.getElementById("include-security"),
            includeGeolocation: document.getElementById("include-geolocation"),
            reportResults: document.getElementById("report-results"),
            exportButtons: document.getElementById("export-buttons"),
            
            // History
            historyList: document.getElementById("history-list"),
            
            // Enhanced Security Dashboard Elements
            securityStatusHeader: document.getElementById("security-status-header"),
            securityStatusTitle: document.querySelector(".security-status-title"),
            securityStatusDescription: document.querySelector(".security-status-description"),
            securityScoreDisplay: document.querySelector(".security-score-number"),
            criticalThreats: document.getElementById("critical-threats"),
            highWarnings: document.getElementById("high-warnings"),
            secureConnectionsNew: document.getElementById("secure-connections"),
            totalConnections: document.getElementById("total-connections"),
            securityTimeline: document.getElementById("security-timeline"),
            metricThreats: document.getElementById("metric-threats"),
            metricWarnings: document.getElementById("metric-warnings"),
            metricSecure: document.getElementById("metric-secure"),
            metricTotal: document.getElementById("metric-total"),
        };
    },

    bindEvents() {
        // Scan buttons
        document.getElementById("btn-investigate")?.addEventListener("click", () => this.runInvestigation(true));
        const debouncedRefresh = this.debounce(() => this.runInvestigation(true), 500);
        document.getElementById("refresh-btn")?.addEventListener("click", debouncedRefresh);
        document.getElementById("btn-export-scan")?.addEventListener("click", () => this.exportInvestigation());

        // Lookup buttons
        document.getElementById("btn-lookup")?.addEventListener("click", () => {
            const ip = this.el.ipInput?.value.trim();
            if (ip) this.lookupIp(ip);
            else notyf.warning("Enter an IP address first");
        });

        // Quick lookup chips
        document.querySelectorAll(".btn-chip[data-ip]").forEach((btn) =>
            btn.addEventListener("click", () => {
                const ip = btn.getAttribute("data-ip");
                if (this.el.ipInput) this.el.ipInput.value = ip;
                this.lookupIp(ip);
            })
        );

        // My IP button
        document.getElementById("my-ip-btn")?.addEventListener("click", async () => {
            const res = await this.fetchJson("/api/myip");
            if (res?.ip && this.el.ipInput) {
                this.el.ipInput.value = res.ip;
                this.lookupIp(res.ip);
            }
        });

        // Map buttons
        document.getElementById("btn-map")?.addEventListener("click", () => this.generateMap());
        document.getElementById("btn-clear-map")?.addEventListener("click", () => this.clearMap());

        // Report buttons
        document.getElementById("btn-report")?.addEventListener("click", () => this.generateReport());
        document.getElementById("btn-download")?.addEventListener("click", () => this.downloadReport());
        document.getElementById("btn-download-pdf")?.addEventListener("click", () =>
            notyf.info("PDF export coming soon")
        );

        // History clear
        document.getElementById("clear-history")?.addEventListener("click", () => {
            this.state.lookupHistory = [];
            localStorage.setItem("ipchecker-history", "[]");
            this.renderHistory();
            notyf.success("History cleared");
        });
        
        // Enter key in IP input
        this.el.ipInput?.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                const ip = this.el.ipInput.value.trim();
                if (ip) this.lookupIp(ip);
            }
        });
    },

    lazyInitTab(id) {
        switch (id) {
            case "dashboard":
                if (!this.state.chartsInitialized) {
                    this.initCharts();
                    this.state.chartsInitialized = true;
                }
                break;
            case "investigate":
                if (!this.state.tableInitialized) {
                    this.initConnectionsTable();
                    this.state.tableInitialized = true;
                }
                break;
            case "map":
                if (!this.state.mapInitialized) {
                    this.initMap();
                    this.state.mapInitialized = true;
                }
                break;
            default:
                break;
        }
    },

    // Enhanced Skeleton Loading States
    showDashboardSkeleton() {
        if (this.el.dashboardSkeleton) {
            this.el.dashboardSkeleton.style.display = "grid";
            // Add shimmer animation
            this.addShimmerEffect(this.el.dashboardSkeleton);
        }
        if (this.el.dashboardContent) this.el.dashboardContent.classList.add("hidden");
    },

    hideDashboardSkeleton() {
        if (this.el.dashboardSkeleton) {
            // Remove shimmer effect
            this.removeShimmerEffect(this.el.dashboardSkeleton);
            
            gsap.to(this.el.dashboardSkeleton, {
                opacity: 0,
                duration: 0.3,
                onComplete: () => {
                    this.el.dashboardSkeleton.style.display = "none";
                    this.el.dashboardSkeleton.style.opacity = 1;
                }
            });
        }
        if (this.el.dashboardContent) {
            this.el.dashboardContent.classList.remove("hidden");
            gsap.from(this.el.dashboardContent.children, {
                y: 20,
                opacity: 0,
                duration: 0.5,
                stagger: 0.1,
                ease: "power2.out"
            });
        }
    },

    // Generic skeleton loader for any container
    showSkeleton(containerId, type = 'default') {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // Hide original content
        const children = Array.from(container.children);
        children.forEach(child => child.style.display = 'none');
        
        // Create skeleton based on type
        let skeletonHtml = '';
        
        switch(type) {
            case 'card':
                skeletonHtml = this.createCardSkeleton();
                break;
            case 'list':
                skeletonHtml = this.createListSkeleton();
                break;
            case 'table':
                skeletonHtml = this.createTableSkeleton();
                break;
            case 'chart':
                skeletonHtml = this.createChartSkeleton();
                break;
            default:
                skeletonHtml = this.createDefaultSkeleton();
        }
        
        container.insertAdjacentHTML('beforeend', skeletonHtml);
        const skeleton = container.querySelector('.enhanced-skeleton');
        if (skeleton) {
            this.addShimmerEffect(skeleton);
        }
        
        // Store reference for cleanup
        container.dataset.skeletonActive = 'true';
        container.dataset.originalChildren = JSON.stringify(children.map(c => c.outerHTML));
    },

    hideSkeleton(containerId) {
        const container = document.getElementById(containerId);
        if (!container || !container.dataset.skeletonActive) return;
        
        // Remove skeleton
        const skeleton = container.querySelector('.enhanced-skeleton');
        if (skeleton) {
            this.removeShimmerEffect(skeleton);
            skeleton.remove();
        }
        
        // Restore original content
        const children = Array.from(container.children);
        children.forEach(child => child.style.display = '');
        
        delete container.dataset.skeletonActive;
        delete container.dataset.originalChildren;
    },

    // Shimmer effect management
    addShimmerEffect(element) {
        if (!element) return;
        
        // Add shimmer CSS if not already present
        if (!document.getElementById('shimmer-styles')) {
            const style = document.createElement('style');
            style.id = 'shimmer-styles';
            style.textContent = `
                @keyframes shimmer {
                    0% { background-position: -1000px 0; }
                    100% { background-position: 1000px 0; }
                }
                .shimmer-effect {
                    background: linear-gradient(to right, 
                        rgba(255,255,255,0.1) 0%,
                        rgba(255,255,255,0.2) 50%,
                        rgba(255,255,255,0.1) 100%);
                    background-size: 1000px 100%;
                    animation: shimmer 2s infinite linear;
                }
                .dark .shimmer-effect {
                    background: linear-gradient(to right, 
                        rgba(255,255,255,0.05) 0%,
                        rgba(255,255,255,0.1) 50%,
                        rgba(255,255,255,0.05) 100%);
                }
            `;
            document.head.appendChild(style);
        }
        
        element.classList.add('shimmer-effect');
    },

    removeShimmerEffect(element) {
        if (element) {
            element.classList.remove('shimmer-effect');
        }
    },

    // Skeleton templates
    createCardSkeleton() {
        return `
            <div class="enhanced-skeleton" style="
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                padding: 1rem;
            ">
                ${Array(4).fill().map(() => `
                    <div style="
                        background: var(--panel-strong);
                        border: 1px solid var(--border);
                        border-radius: var(--radius);
                        padding: 1rem;
                        height: 120px;
                        display: flex;
                        flex-direction: column;
                        gap: 0.75rem;
                    ">
                        <div style="
                            height: 24px;
                            background: var(--border);
                            border-radius: 4px;
                            width: 60%;
                        "></div>
                        <div style="
                            height: 32px;
                            background: var(--border);
                            border-radius: 6px;
                            width: 80%;
                        "></div>
                        <div style="
                            height: 16px;
                            background: var(--border);
                            border-radius: 3px;
                            width: 40%;
                        "></div>
                    </div>
                `).join('')}
            </div>
        `;
    },

    createListSkeleton() {
        return `
            <div class="enhanced-skeleton" style="
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
                padding: 1rem;
            ">
                ${Array(6).fill().map(() => `
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 1rem;
                        padding: 1rem;
                        background: var(--panel-strong);
                        border: 1px solid var(--border);
                        border-radius: var(--radius-small);
                    ">
                        <div style="
                            width: 40px;
                            height: 40px;
                            border-radius: 50%;
                            background: var(--border);
                        "></div>
                        <div style="flex: 1;">
                            <div style="
                                height: 16px;
                                background: var(--border);
                                border-radius: 3px;
                                width: 30%;
                                margin-bottom: 0.5rem;
                            "></div>
                            <div style="
                                height: 14px;
                                background: var(--border);
                                border-radius: 3px;
                                width: 70%;
                            "></div>
                        </div>
                        <div style="
                            height: 24px;
                            background: var(--border);
                            border-radius: 4px;
                            width: 80px;
                        "></div>
                    </div>
                `).join('')}
            </div>
        `;
    },

    createTableSkeleton() {
        return `
            <div class="enhanced-skeleton" style="padding: 1rem;">
                <div style="
                    display: grid;
                    grid-template-columns: repeat(5, 1fr);
                    gap: 0.5rem;
                    margin-bottom: 1rem;
                ">
                    ${Array(5).fill().map(() => `
                        <div style="
                            height: 20px;
                            background: var(--border);
                            border-radius: 4px;
                        "></div>
                    `).join('')}
                </div>
                ${Array(8).fill().map(() => `
                    <div style="
                        display: grid;
                        grid-template-columns: repeat(5, 1fr);
                        gap: 0.5rem;
                        padding: 0.75rem 0;
                        border-bottom: 1px solid var(--border);
                    ">
                        ${Array(5).fill().map(() => `
                            <div style="
                                height: 16px;
                                background: var(--border);
                                border-radius: 3px;
                            "></div>
                        `).join('')}
                    </div>
                `).join('')}
            </div>
        `;
    },

    createChartSkeleton() {
        return `
            <div class="enhanced-skeleton" style="
                padding: 1rem;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
            ">
                <div style="
                    background: var(--panel-strong);
                    border: 1px solid var(--border);
                    border-radius: var(--radius);
                    height: 300px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                ">
                    <div style="
                        text-align: center;
                        color: var(--text-muted);
                    ">
                        <div style="
                            width: 60px;
                            height: 60px;
                            background: var(--border);
                            border-radius: 50%;
                            margin: 0 auto 1rem;
                        "></div>
                        <div>Loading Chart Data...</div>
                    </div>
                </div>
                <div style="
                    background: var(--panel-strong);
                    border: 1px solid var(--border);
                    border-radius: var(--radius);
                    height: 300px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                ">
                    <div style="
                        text-align: center;
                        color: var(--text-muted);
                    ">
                        <div style="
                            width: 60px;
                            height: 60px;
                            background: var(--border);
                            border-radius: 50%;
                            margin: 0 auto 1rem;
                        "></div>
                        <div>Loading Chart Data...</div>
                    </div>
                </div>
            </div>
        `;
    },

    createDefaultSkeleton() {
        return `
            <div class="enhanced-skeleton" style="
                padding: 2rem;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 200px;
            ">
                <div style="
                    width: 80px;
                    height: 80px;
                    background: var(--border);
                    border-radius: 50%;
                    margin-bottom: 1rem;
                    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
                "></div>
                <div style="
                    height: 20px;
                    background: var(--border);
                    border-radius: 4px;
                    width: 200px;
                    margin-bottom: 0.5rem;
                "></div>
                <div style="
                    height: 16px;
                    background: var(--border);
                    border-radius: 3px;
                    width: 150px;
                "></div>
            </div>
        `;
    },

    // Progress loading indicator
    showProgressLoader(message = 'Loading...', containerId = null) {
        const container = containerId ? document.getElementById(containerId) : document.body;
        if (!container) return;
        
        const loader = document.createElement('div');
        loader.className = 'progress-loader';
        loader.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 4px;
                background: var(--bg);
                z-index: 9999;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            ">
                <div style="
                    height: 100%;
                    width: 0%;
                    background: linear-gradient(90deg, var(--primary), var(--primary-2));
                    transition: width 0.3s ease;
                    border-radius: 0 2px 2px 0;
                " class="progress-bar"></div>
            </div>
            <div style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: var(--radius);
                padding: 2rem;
                text-align: center;
                box-shadow: var(--shadow-large);
                z-index: 10000;
                min-width: 250px;
            ">
                <div style="
                    width: 50px;
                    height: 50px;
                    border: 3px solid var(--border);
                    border-top: 3px solid var(--primary);
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 1rem;
                "></div>
                <div style="color: var(--text); font-weight: 500;">${message}</div>
                <div style="color: var(--text-muted); font-size: 0.875rem; margin-top: 0.5rem;">Please wait...</div>
            </div>
        `;
        
        // Add spinner animation if not exists
        if (!document.getElementById('spinner-styles')) {
            const style = document.createElement('style');
            style.id = 'spinner-styles';
            style.textContent = `
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
            `;
            document.head.appendChild(style);
        }
        
        container.appendChild(loader);
        
        // Simulate progress
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress >= 90) progress = 90; // Cap at 90% to avoid completion
            const progressBar = loader.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = `${progress}%`;
            }
        }, 200);
        
        // Store reference
        loader.dataset.intervalId = interval;
        
        return loader;
    },

    hideProgressLoader(loaderElement) {
        if (!loaderElement) return;
        
        // Clear progress interval
        const intervalId = loaderElement.dataset.intervalId;
        if (intervalId) {
            clearInterval(parseInt(intervalId));
        }
        
        // Complete progress and fade out
        const progressBar = loaderElement.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = '100%';
        }
        
        setTimeout(() => {
            loaderElement.style.opacity = '0';
            loaderElement.style.transition = 'opacity 0.3s ease';
            setTimeout(() => {
                if (loaderElement.parentNode) {
                    loaderElement.parentNode.removeChild(loaderElement);
                }
            }, 300);
        }, 300);
    },

    // Enhanced Form Validation and Accessibility
    initFormValidation() {
        // Initialize all forms with validation
        const forms = document.querySelectorAll('form[data-validate]');
        forms.forEach(form => this.enhanceForm(form));
        
        // Set up real-time validation
        this.setupRealTimeValidation();
        
        // Add accessibility features
        this.enhanceFormAccessibility();
        
        // Set up form submission handling
        this.setupFormSubmission();
    },

    enhanceForm(form) {
        // Add validation attributes
        form.setAttribute('novalidate', 'true');
        
        // Add form identifier
        if (!form.id) {
            form.id = `form-${Date.now()}`;
        }
        
        // Process form fields
        const fields = form.querySelectorAll('input, select, textarea');
        fields.forEach(field => this.enhanceFormField(field, form));
        
        // Add form-level validation
        form.addEventListener('submit', (e) => this.handleFormSubmit(e, form));
    },

    enhanceFormField(field, form) {
        // Add required attributes
        if (field.hasAttribute('required')) {
            field.setAttribute('aria-required', 'true');
        }
        
        // Add descriptive labels
        const label = this.getFieldLabel(field);
        if (label) {
            field.setAttribute('aria-labelledby', label.id || `label-${field.id || Date.now()}`);
        }
        
        // Add validation patterns
        this.addFieldValidation(field);
        
        // Add real-time validation listeners
        field.addEventListener('blur', () => this.validateField(field));
        field.addEventListener('input', () => this.clearFieldError(field));
        
        // Add accessibility attributes
        this.addFieldAccessibility(field);
        
        // Add autocomplete where appropriate
        this.addFieldAutocomplete(field);
    },

    getFieldLabel(field) {
        // Find associated label
        const id = field.id;
        if (id) {
            const label = document.querySelector(`label[for="${id}"]`);
            if (label) return label;
        }
        
        // Check if label is wrapped around the field
        const parentLabel = field.closest('label');
        if (parentLabel) return parentLabel;
        
        // Create label if none exists
        return this.createFieldLabel(field);
    },

    createFieldLabel(field) {
        const label = document.createElement('label');
        label.textContent = field.placeholder || field.name || 'Field';
        label.setAttribute('for', field.id || `field-${Date.now()}`);
        
        if (!field.id) {
            field.id = label.getAttribute('for');
        }
        
        field.parentNode.insertBefore(label, field);
        return label;
    },

    addFieldValidation(field) {
        const type = field.type;
        const name = field.name || field.id;
        
        // Add appropriate validation based on field type
        switch(type) {
            case 'email':
                field.pattern = '[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$';
                field.title = 'Please enter a valid email address';
                break;
                
            case 'url':
                field.pattern = 'https?://.+';
                field.title = 'Please enter a valid URL';
                break;
                
            case 'tel':
                field.pattern = '[0-9+\-\s\(\)]+';
                field.title = 'Please enter a valid phone number';
                break;
                
            case 'number':
                if (!field.min) field.min = 0;
                if (!field.step) field.step = 1;
                break;
                
            default:
                // Custom validation for IP addresses
                if (name && (name.includes('ip') || name.includes('address'))) {
                    field.pattern = '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]+|::(ffff(:0{1,4})?:)?((25[0-5]|(2[0-4]|1?[0-9])?[0-9])\.){3}(25[0-5]|(2[0-4]|1?[0-9])?[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1?[0-9])?[0-9])\.){3}(25[0-5]|(2[0-4]|1?[0-9])?[0-9]))$';
                    field.title = 'Please enter a valid IPv4 or IPv6 address';
                }
        }
        
        // Add custom validation for textarea inputs
        if (field.tagName === 'TEXTAREA') {
            if (!field.minLength) field.minLength = 1;
            if (!field.maxLength) field.maxLength = 1000;
        }
    },

    addFieldAccessibility(field) {
        // Ensure proper ARIA roles
        if (field.tagName === 'INPUT' && field.type === 'checkbox') {
            field.setAttribute('role', 'checkbox');
        } else if (field.tagName === 'SELECT') {
            field.setAttribute('role', 'combobox');
        } else if (field.tagName === 'TEXTAREA') {
            field.setAttribute('role', 'textbox');
        }
        
        // Add descriptive error messages
        const errorId = `error-${field.id || Date.now()}`;
        field.setAttribute('aria-describedby', errorId);
        
        // Create error container
        const errorContainer = document.createElement('div');
        errorContainer.id = errorId;
        errorContainer.className = 'field-error';
        errorContainer.setAttribute('aria-live', 'polite');
        errorContainer.setAttribute('aria-atomic', 'true');
        
        field.parentNode.insertBefore(errorContainer, field.nextSibling);
    },

    addFieldAutocomplete(field) {
        const name = field.name || field.id;
        
        // Add autocomplete attributes based on field purpose
        if (!field.autocomplete) {
            if (name.includes('email')) {
                field.autocomplete = 'email';
            } else if (name.includes('name')) {
                field.autocomplete = 'name';
            } else if (name.includes('password')) {
                field.autocomplete = 'current-password';
            } else if (name.includes('ip') || name.includes('address')) {
                field.autocomplete = 'off';
            } else if (field.type === 'search') {
                field.autocomplete = 'off';
            }
        }
    },

    setupRealTimeValidation() {
        // Debounced validation to prevent excessive checking
        let validationTimeout;
        
        document.addEventListener('input', (e) => {
            clearTimeout(validationTimeout);
            validationTimeout = setTimeout(() => {
                if (e.target.matches('input, select, textarea')) {
                    this.validateField(e.target);
                }
            }, 300);
        });
    },

    validateField(field) {
        const value = field.value.trim();
        const errors = [];
        
        // Required field validation
        if (field.hasAttribute('required') && !value) {
            errors.push('This field is required');
        }
        
        // Pattern validation
        if (field.pattern && value) {
            const regex = new RegExp(field.pattern);
            if (!regex.test(value)) {
                errors.push(field.title || 'Please enter a valid value');
            }
        }
        
        // Length validation
        if (field.minLength && value.length < field.minLength) {
            errors.push(`Minimum ${field.minLength} characters required`);
        }
        
        if (field.maxLength && value.length > field.maxLength) {
            errors.push(`Maximum ${field.maxLength} characters allowed`);
        }
        
        // Number validation
        if (field.type === 'number' && value) {
            const num = parseFloat(value);
            if (isNaN(num)) {
                errors.push('Please enter a valid number');
            } else {
                if (field.min !== undefined && num < parseFloat(field.min)) {
                    errors.push(`Value must be at least ${field.min}`);
                }
                if (field.max !== undefined && num > parseFloat(field.max)) {
                    errors.push(`Value must be no more than ${field.max}`);
                }
            }
        }
        
        // Custom validations
        if (field.dataset.customValidate) {
            const customErrors = this.runCustomValidation(field, value);
            errors.push(...customErrors);
        }
        
        // Display validation result
        if (errors.length > 0) {
            this.showFieldError(field, errors[0]);
            return false;
        } else {
            this.clearFieldError(field);
            return true;
        }
    },

    runCustomValidation(field, value) {
        const errors = [];
        const validators = field.dataset.customValidate.split(',');
        
        validators.forEach(validator => {
            switch(validator.trim()) {
                case 'ip-address':
                    if (value && !this.isValidIPAddress(value)) {
                        errors.push('Please enter a valid IP address');
                    }
                    break;
                case 'domain':
                    if (value && !this.isValidDomain(value)) {
                        errors.push('Please enter a valid domain name');
                    }
                    break;
                case 'cidr':
                    if (value && !this.isValidCIDR(value)) {
                        errors.push('Please enter a valid CIDR notation');
                    }
                    break;
            }
        });
        
        return errors;
    },

    isValidIPAddress(ip) {
        const ipv4Regex = /^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        const ipv6Regex = /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]+|::(ffff(:0{1,4})?:)?((25[0-5]|(2[0-4]|1?[0-9])?[0-9])\.){3}(25[0-5]|(2[0-4]|1?[0-9])?[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1?[0-9])?[0-9])\.){3}(25[0-5]|(2[0-4]|1?[0-9])?[0-9]))$/;
        return ipv4Regex.test(ip) || ipv6Regex.test(ip);
    },

    isValidDomain(domain) {
        const domainRegex = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
        return domainRegex.test(domain) && domain.length <= 253;
    },

    isValidCIDR(cidr) {
        const cidrRegex = /^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/([0-9]|[1-2][0-9]|3[0-2])$/;
        return cidrRegex.test(cidr);
    },

    showFieldError(field, message) {
        field.classList.add('error');
        field.setAttribute('aria-invalid', 'true');
        
        const errorContainer = field.parentNode.querySelector('.field-error');
        if (errorContainer) {
            errorContainer.textContent = message;
            errorContainer.style.display = 'block';
        }
        
        // Add visual indication
        field.style.borderColor = 'var(--danger)';
    },

    clearFieldError(field) {
        field.classList.remove('error');
        field.setAttribute('aria-invalid', 'false');
        
        const errorContainer = field.parentNode.querySelector('.field-error');
        if (errorContainer) {
            errorContainer.textContent = '';
            errorContainer.style.display = 'none';
        }
        
        // Reset border color
        field.style.borderColor = '';
    },

    handleFormSubmit(e, form) {
        e.preventDefault();
        
        // Validate all fields
        const fields = form.querySelectorAll('input, select, textarea');
        let isValid = true;
        
        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        if (isValid) {
            // Form is valid, proceed with submission
            this.submitForm(form);
        } else {
            // Focus first invalid field
            const firstInvalid = form.querySelector('.error');
            if (firstInvalid) {
                firstInvalid.focus();
            }
            
            // Show error notification
            notyf.error('Please correct the errors in the form');
        }
    },

    submitForm(form) {
        const formData = new FormData(form);
        const data = {};
        
        // Convert FormData to object
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        // Add loading state
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
        }
        
        // Submit form data
        this.processFormData(data, form)
            .then(response => {
                notyf.success('Form submitted successfully');
                form.reset();
                this.clearAllFieldErrors(form);
            })
            .catch(error => {
                notyf.error(`Submission failed: ${error.message}`);
            })
            .finally(() => {
                // Reset submit button
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = submitButton.dataset.originalText || 'Submit';
                }
            });
    },

    async processFormData(data, form) {
        // Process form data based on form type
        const formType = form.dataset.formType;
        
        switch(formType) {
            case 'ip-lookup':
                return await this.processIPLookup(data);
            case 'bulk-scan':
                return await this.processBulkScan(data);
            case 'report-settings':
                return await this.processReportSettings(data);
            default:
                return await this.processGenericForm(data);
        }
    },

    async processIPLookup(data) {
        if (data.ip) {
            await this.lookupIp(data.ip);
        }
        return { success: true };
    },

    async processBulkScan(data) {
        if (data.ips) {
            const ips = data.ips.split(/[\n,]/).map(ip => ip.trim()).filter(Boolean);
            await this.bulkLookup(ips);
        }
        return { success: true };
    },

    async processReportSettings(data) {
        // Store report settings
        localStorage.setItem('reportSettings', JSON.stringify(data));
        return { success: true };
    },

    async processGenericForm(data) {
        // Generic form processing
        console.log('Processing form data:', data);
        return { success: true };
    },

    clearAllFieldErrors(form) {
        const fields = form.querySelectorAll('input, select, textarea');
        fields.forEach(field => this.clearFieldError(field));
    },

    enhanceFormAccessibility() {
        // Add form instructions
        const forms = document.querySelectorAll('form[data-validate]');
        forms.forEach(form => {
            const instruction = document.createElement('div');
            instruction.className = 'form-instructions';
            instruction.innerHTML = `
                <small style="color: var(--text-muted); display: block; margin-bottom: 1rem;">
                    <i class="fas fa-info-circle"></i> Required fields are marked with *
                </small>
            `;
            form.insertBefore(instruction, form.firstChild);
        });
        
        // Add live regions for form messages
        if (!document.getElementById('form-messages')) {
            const liveRegion = document.createElement('div');
            liveRegion.id = 'form-messages';
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('aria-atomic', 'true');
            liveRegion.style.position = 'absolute';
            liveRegion.style.left = '-10000px';
            document.body.appendChild(liveRegion);
        }
    },

    setupFormSubmission() {
        // Handle form submissions globally
        document.addEventListener('submit', (e) => {
            if (e.target.matches('form[data-validate]')) {
                // Form will be handled by our validation system
                return;
            }
            
            // Handle other forms normally
            this.handleLegacyFormSubmit(e);
        });
    },

    handleLegacyFormSubmit(e) {
        // Handle legacy forms that don't use our validation system
        const form = e.target;
        const submitButton = form.querySelector('button[type="submit"]');
        
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.dataset.originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        }
    },
    initKeyboardNavigation() {
        // Tab navigation enhancement
        this.setupTabNavigation();
        
        // Keyboard shortcuts
        this.setupKeyboardShortcuts();
        
        // Focus management
        this.setupFocusManagement();
        
        // Skip to content functionality
        this.setupSkipLinks();
        
        // Modal keyboard handling
        this.setupModalKeyboardHandling();
    },

    setupTabNavigation() {
        // Enhanced tab navigation with visual indicators
        const tabs = document.querySelectorAll('[data-tab]');
        const tabContents = document.querySelectorAll('[data-tab-content]');
        
        tabs.forEach(tab => {
            // Add keyboard accessibility
            tab.setAttribute('tabindex', '0');
            tab.setAttribute('role', 'tab');
            
            // Handle keyboard events
            tab.addEventListener('keydown', (e) => {
                switch(e.key) {
                    case 'Enter':
                    case ' ':
                        e.preventDefault();
                        this.switchTab(tab.dataset.tab);
                        break;
                    case 'ArrowRight':
                        e.preventDefault();
                        this.focusNextTab(tab);
                        break;
                    case 'ArrowLeft':
                        e.preventDefault();
                        this.focusPreviousTab(tab);
                        break;
                    case 'Home':
                        e.preventDefault();
                        this.focusFirstTab();
                        break;
                    case 'End':
                        e.preventDefault();
                        this.focusLastTab();
                        break;
                }
            });
            
            // Add focus styling
            tab.addEventListener('focus', () => {
                tab.classList.add('focused');
            });
            
            tab.addEventListener('blur', () => {
                tab.classList.remove('focused');
            });
        });
        
        // Set ARIA attributes
        this.updateTabARIA();
    },

    switchTab(tabId) {
        const tabs = document.querySelectorAll('[data-tab]');
        const tabContents = document.querySelectorAll('[data-tab-content]');
        
        // Update tabs
        tabs.forEach(tab => {
            if (tab.dataset.tab === tabId) {
                tab.classList.add('active');
                tab.setAttribute('aria-selected', 'true');
                tab.setAttribute('tabindex', '0');
            } else {
                tab.classList.remove('active');
                tab.setAttribute('aria-selected', 'false');
                tab.setAttribute('tabindex', '-1');
            }
        });
        
        // Update content
        tabContents.forEach(content => {
            if (content.dataset.tabContent === tabId) {
                content.classList.add('active');
                content.removeAttribute('inert');
                content.removeAttribute('aria-hidden');
            } else {
                content.classList.remove('active');
                content.setAttribute('inert', '');
            }
        });
        
        // Update ARIA
        this.updateTabARIA();
        
        // Trigger tab change event
        this.onTabChange(tabId);
    },

    focusNextTab(currentTab) {
        const tabs = Array.from(document.querySelectorAll('[data-tab]'));
        const currentIndex = tabs.indexOf(currentTab);
        const nextIndex = (currentIndex + 1) % tabs.length;
        tabs[nextIndex].focus();
    },

    focusPreviousTab(currentTab) {
        const tabs = Array.from(document.querySelectorAll('[data-tab]'));
        const currentIndex = tabs.indexOf(currentTab);
        const prevIndex = (currentIndex - 1 + tabs.length) % tabs.length;
        tabs[prevIndex].focus();
    },

    focusFirstTab() {
        const firstTab = document.querySelector('[data-tab]:first-child');
        if (firstTab) firstTab.focus();
    },

    focusLastTab() {
        const lastTab = document.querySelector('[data-tab]:last-child');
        if (lastTab) lastTab.focus();
    },

    updateTabARIA() {
        const tabs = document.querySelectorAll('[data-tab]');
        const tabContents = document.querySelectorAll('[data-tab-content]');
        
        // Create tab list
        const tabList = document.createElement('div');
        tabList.setAttribute('role', 'tablist');
        
        tabs.forEach((tab, index) => {
            tab.setAttribute('role', 'tab');
            tab.setAttribute('aria-controls', `tabpanel-${index}`);
            
            const content = tabContents[index];
            if (content) {
                content.setAttribute('role', 'tabpanel');
                content.setAttribute('id', `tabpanel-${index}`);
                content.setAttribute('aria-labelledby', tab.id || `tab-${index}`);
            }
        });
    },

    setupKeyboardShortcuts() {
        const shortcuts = {
            // Global shortcuts
            'ctrl+d': () => this.toggleDarkMode(),
            'ctrl+k': () => this.focusSearch(),
            'ctrl+r': () => this.runInvestigation(true),
            'ctrl+l': () => this.clearAllData(),
            
            // Tab navigation
            'alt+1': () => this.switchTab('dashboard'),
            'alt+2': () => this.switchTab('lookup'),
            'alt+3': () => this.switchTab('map'),
            'alt+4': () => this.switchTab('reports'),
            'alt+5': () => this.switchTab('settings'),
            
            // Action shortcuts
            'ctrl+s': () => this.saveCurrentState(),
            'ctrl+z': () => this.undoLastAction(),
            'ctrl+shift+z': () => this.redoLastAction(),
            
            // Navigation
            'ctrl+arrowleft': () => this.navigateToPrevious(),
            'ctrl+arrowright': () => this.navigateToNext()
        };
        
        document.addEventListener('keydown', (e) => {
            // Check for shortcut combinations
            const keyCombo = this.getKeyCombo(e);
            
            if (shortcuts[keyCombo]) {
                e.preventDefault();
                shortcuts[keyCombo]();
            }
            
            // Escape key handling
            if (e.key === 'Escape') {
                this.handleEscapeKey();
            }
        });
        
        // Display shortcuts helper
        this.createShortcutHelper(shortcuts);
    },

    getKeyCombo(e) {
        const modifiers = [];
        if (e.ctrlKey) modifiers.push('ctrl');
        if (e.altKey) modifiers.push('alt');
        if (e.shiftKey) modifiers.push('shift');
        if (e.metaKey) modifiers.push('meta');
        
        const key = e.key.toLowerCase();
        return [...modifiers, key].join('+');
    },

    setupFocusManagement() {
        // Focus trap for modals
        this.focusTrapElements = [];
        
        // Auto-focus first focusable element
        this.autoFocusFirstElement();
        
        // Manage focus outlines
        this.manageFocusOutlines();
        
        // Focus restoration
        this.setupFocusRestoration();
    },

    autoFocusFirstElement() {
        // Auto-focus search/input fields on page load
        const autoFocusElements = document.querySelectorAll('[data-autofocus]');
        if (autoFocusElements.length > 0) {
            autoFocusElements[0].focus();
        }
    },

    manageFocusOutlines() {
        // Only show focus outlines when using keyboard
        let isUsingKeyboard = false;
        
        document.addEventListener('keydown', () => {
            isUsingKeyboard = true;
            document.body.classList.add('using-keyboard');
        });
        
        document.addEventListener('mousedown', () => {
            isUsingKeyboard = false;
            document.body.classList.remove('using-keyboard');
        });
    },

    setupFocusRestoration() {
        // Save focus state before navigation
        window.addEventListener('beforeunload', () => {
            const activeElement = document.activeElement;
            if (activeElement && activeElement.id) {
                sessionStorage.setItem('lastFocusedElement', activeElement.id);
            }
        });
        
        // Restore focus on page load
        window.addEventListener('load', () => {
            const lastFocusedId = sessionStorage.getItem('lastFocusedElement');
            if (lastFocusedId) {
                const element = document.getElementById(lastFocusedId);
                if (element) {
                    element.focus();
                }
                sessionStorage.removeItem('lastFocusedElement');
            }
        });
    },

    setupSkipLinks() {
        // Create skip to main content link
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.textContent = 'Skip to main content';
        skipLink.className = 'skip-link';
        skipLink.setAttribute('aria-label', 'Skip to main content');
        
        // Add CSS for skip link
        if (!document.getElementById('skip-link-styles')) {
            const style = document.createElement('style');
            style.id = 'skip-link-styles';
            style.textContent = `
                .skip-link {
                    position: absolute;
                    top: -40px;
                    left: 0;
                    background: var(--primary);
                    color: var(--bg);
                    padding: 8px 16px;
                    text-decoration: none;
                    border-radius: 0 0 4px 4px;
                    z-index: 10000;
                    transition: top 0.2s ease;
                }
                .skip-link:focus {
                    top: 0;
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.insertBefore(skipLink, document.body.firstChild);
    },

    setupModalKeyboardHandling() {
        // Handle modal-specific keyboard interactions
        document.addEventListener('keydown', (e) => {
            if (this.isModalOpen()) {
                switch(e.key) {
                    case 'Escape':
                        this.closeModal();
                        break;
                    case 'Tab':
                        this.handleModalTabbing(e);
                        break;
                }
            }
        });
    },

    isModalOpen() {
        return document.querySelector('.modal.show') !== null;
    },

    closeModal() {
        const modal = document.querySelector('.modal.show');
        if (modal) {
            modal.classList.remove('show');
            // Restore focus to trigger element
            const trigger = modal.triggerElement;
            if (trigger) trigger.focus();
        }
    },

    handleModalTabbing(e) {
        const modal = document.querySelector('.modal.show');
        if (!modal) return;
        
        const focusableElements = modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        
        if (e.shiftKey) {
            if (document.activeElement === firstElement) {
                e.preventDefault();
                lastElement.focus();
            }
        } else {
            if (document.activeElement === lastElement) {
                e.preventDefault();
                firstElement.focus();
            }
        }
    },

    handleEscapeKey() {
        // Close modals, dropdowns, tooltips
        if (this.isModalOpen()) {
            this.closeModal();
        }
        
        // Close dropdowns
        const openDropdowns = document.querySelectorAll('.dropdown.show');
        openDropdowns.forEach(dropdown => {
            dropdown.classList.remove('show');
        });
        
        // Close tooltips
        const tooltips = document.querySelectorAll('.tooltip');
        tooltips.forEach(tooltip => {
            tooltip.remove();
        });
    },

    createShortcutHelper(shortcuts) {
        // Create keyboard shortcut helper modal
        const helperButton = document.createElement('button');
        helperButton.innerHTML = '<i class="fas fa-keyboard"></i>';
        helperButton.className = 'btn-icon btn-ghost keyboard-helper-btn';
        helperButton.setAttribute('aria-label', 'Show keyboard shortcuts');
        helperButton.addEventListener('click', () => this.showShortcutHelper(shortcuts));
        
        // Add to header actions
        const headerActions = document.querySelector('.header-actions');
        if (headerActions) {
            headerActions.appendChild(helperButton);
        }
    },

    showShortcutHelper(shortcuts) {
        const modal = document.createElement('div');
        modal.className = 'modal show';
        modal.innerHTML = `
            <div style="
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: var(--radius);
                padding: 2rem;
                max-width: 500px;
                width: 90vw;
                max-height: 80vh;
                overflow-y: auto;
            ">
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 1.5rem;
                ">
                    <h2 style="margin: 0; color: var(--text);">Keyboard Shortcuts</h2>
                    <button class="btn-icon btn-ghost" onclick="this.closest('.modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div style="display: grid; gap: 1rem;">
                    ${Object.entries(shortcuts).map(([combo, action]) => `
                        <div style="
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            padding: 0.75rem;
                            background: var(--bg-secondary);
                            border-radius: var(--radius-small);
                        ">
                            <kbd style="
                                background: var(--border);
                                padding: 0.25rem 0.5rem;
                                border-radius: 4px;
                                font-family: monospace;
                                font-size: 0.875rem;
                            ">${combo.replace('+', ' + ').toUpperCase()}</kbd>
                            <span style="color: var(--text-muted); font-size: 0.875rem;">
                                ${this.getShortcutDescription(combo)}
                            </span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    },

    getShortcutDescription(combo) {
        const descriptions = {
            'ctrl+d': 'Toggle Dark Mode',
            'ctrl+k': 'Focus Search',
            'ctrl+r': 'Refresh Dashboard',
            'ctrl+l': 'Clear All Data',
            'alt+1': 'Dashboard Tab',
            'alt+2': 'Lookup Tab',
            'alt+3': 'Map Tab',
            'alt+4': 'Reports Tab',
            'alt+5': 'Settings Tab',
            'ctrl+s': 'Save State',
            'ctrl+z': 'Undo',
            'ctrl+shift+z': 'Redo',
            'ctrl+arrowleft': 'Previous',
            'ctrl+arrowright': 'Next'
        };
        return descriptions[combo] || 'Unknown Action';
    },

    // Event handlers
    onTabChange(tabId) {
        // Custom tab change logic
        console.log(`Switched to tab: ${tabId}`);
        
        // Update URL hash
        window.location.hash = tabId;
        
        // Analytics or other tracking
        this.trackTabChange(tabId);
    },

    trackTabChange(tabId) {
        // Implement analytics tracking
        if (window.gtag) {
            gtag('event', 'tab_change', {
                'tab_id': tabId
            });
        }
    },

    toggleDarkMode() {
        document.body.classList.toggle('light-theme');
        const isLight = document.body.classList.contains('light-theme');
        localStorage.setItem('theme', isLight ? 'light' : 'dark');
    },

    focusSearch() {
        const searchInput = document.querySelector('[data-search]') || 
                           document.querySelector('input[type="search"]') ||
                           document.querySelector('input[type="text"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    },

    clearAllData() {
        if (confirm('Are you sure you want to clear all data?')) {
            localStorage.clear();
            location.reload();
        }
    },

    saveCurrentState() {
        // Implement state saving logic
        const state = {
            timestamp: new Date().toISOString(),
            currentTab: document.querySelector('[data-tab].active')?.dataset.tab,
            formData: this.collectFormData()
        };
        
        localStorage.setItem('appState', JSON.stringify(state));
        notyf.success('State saved successfully');
    },

    collectFormData() {
        const forms = document.querySelectorAll('form');
        const data = {};
        
        forms.forEach(form => {
            const formData = new FormData(form);
            for (let [key, value] of formData.entries()) {
                data[key] = value;
            }
        });
        
        return data;
    },

    undoLastAction() {
        // Implement undo functionality
        notyf.info('Undo functionality coming soon');
    },

    redoLastAction() {
        // Implement redo functionality
        notyf.info('Redo functionality coming soon');
    },

    navigateToPrevious() {
        // Implement previous navigation
        history.back();
    },

    navigateToNext() {
        // Implement next navigation
        history.forward();
    },
    animateEntrance() {
        gsap.from(".sidebar", {
            x: -50,
            opacity: 0,
            duration: 0.6,
            ease: "power3.out"
        });
        
        gsap.from(".top-header", {
            y: -20,
            opacity: 0,
            duration: 0.5,
            delay: 0.2,
            ease: "power2.out"
        });
    },

    animateStatCards() {
        gsap.from(".stat-card", {
            y: 30,
            opacity: 0,
            duration: 0.6,
            stagger: 0.1,
            ease: "back.out(1.7)"
        });
    },

    animateCounter(element, targetValue) {
        const obj = { val: 0 };
        gsap.to(obj, {
            val: targetValue,
            duration: 1.5,
            ease: "power2.out",
            onUpdate: () => {
                element.textContent = Math.round(obj.val);
            }
        });
    },

    // Data Operations
    async runInvestigation(showNotification = false) {
        if (!this.el.scanProgress) return;
        this.el.scanProgress.style.display = "flex";
        this.updateProgress(15);
        this.setLoading(true);
        
        try {
            const data = await this.fetchJson("/api/investigate");
            if (!data) throw new Error("No data returned");
            
            this.state.investigation = data;
            this.hideDashboardSkeleton();
            this.updateInvestigation(data);
            this.updateDashboard(data);
            this.updateSecurity(data.security, data.connections);
            
            const exportBtn = document.getElementById("btn-export-scan");
            if (exportBtn) exportBtn.disabled = false;
            
            this.pushActivity("PC investigation completed");
            if (showNotification) notyf.success("Investigation finished");
            this.saveHistoryEntry({ type: "investigation", at: data.timestamp });
            
        } catch (err) {
            notyf.error(`Investigation failed: ${err.message || err}`);
        } finally {
            this.updateProgress(100);
            setTimeout(() => (this.el.scanProgress.style.display = "none"), 500);
            this.setLoading(false);
        }
    },

    updateProgress(val) {
        if (this.el.progressFill) this.el.progressFill.style.width = `${val}%`;
    },

    updateDashboard(info) {
        const security = info.security || {};
        const stats = {
            connections: info.summary?.total_connections ?? 0,
            secure: security.secure ?? 0,
            warnings: security.warnings ?? 0,
            threats: security.threats ?? 0
        };
        
        // Animate counters
        if (this.el.activeConnections) {
            this.el.activeConnections.dataset.value = stats.connections;
            this.animateCounter(this.el.activeConnections, stats.connections);
        }
        if (this.el.secureConnections) {
            this.el.secureConnections.dataset.value = stats.secure;
            this.animateCounter(this.el.secureConnections, stats.secure);
        }
        if (this.el.warningsCount) {
            this.el.warningsCount.dataset.value = stats.warnings;
            this.animateCounter(this.el.warningsCount, stats.warnings);
        }
        if (this.el.threatsCount) {
            this.el.threatsCount.dataset.value = stats.threats;
            this.animateCounter(this.el.threatsCount, stats.threats);
        }
        
        // Update enhanced security dashboard
        this.updateSecurityDashboard(security, info);
        
        this.updateCharts(info);
        this.pushActivity("Dashboard updated");
    },

    updateInvestigation(info) {
        if (this.el.sysHostname) this.el.sysHostname.textContent = info.hostname || "-";
        if (this.el.sysPlatform) this.el.sysPlatform.textContent = info.platform || "-";
        if (this.el.sysTime) this.el.sysTime.textContent = this.formatDate(info.timestamp);
        if (this.el.sysInterfaces) this.el.sysInterfaces.textContent = info.interfaces?.length || 0;

        // Interfaces
        if (this.el.interfacesList) {
            this.el.interfacesList.innerHTML = "";
            (info.interfaces || []).forEach((iface, index) => {
                const div = document.createElement("div");
                div.className = "interface-card";
                const addresses = (iface.addresses || [])
                    .map((a) => `${a.family}: ${a.address}${a.netmask ? " /" + a.netmask : ""}`)
                    .join("<br>");
                div.innerHTML = `<h4>${iface.name}</h4><p>${addresses || "No addresses"}</p>`;
                this.el.interfacesList.appendChild(div);
                
                // Animate each interface card
                gsap.from(div, {
                    x: -20,
                    opacity: 0,
                    duration: 0.4,
                    delay: index * 0.05,
                    ease: "power2.out"
                });
            });
        }

        // Update Tabulator table
        if (this.state.connectionsTable) {
            const tableData = (info.connections || []).map(conn => ({
                protocol: conn.protocol || "-",
                local_addr: conn.local_addr || "-",
                remote_addr: conn.remote_addr || "-",
                status: conn.status || "-",
                process: conn.process || "-",
                location: this.formatGeo(conn.geo),
                risk_level: conn.risk_level || "info",
                _raw: conn // Keep raw data for reference
            }));
            this.state.connectionsTable.setData(tableData);
        }
    },

    // Enhanced ApexCharts Implementation
    initCharts() {
        // Connection Types Chart (Enhanced Donut with Animations)
        if (this.el.connectionChart) {
            this.state.charts.connections = new ApexCharts(this.el.connectionChart, {
                series: [0, 0],
                labels: ["TCP", "UDP"],
                chart: {
                    type: 'donut',
                    height: 300,
                    fontFamily: 'Inter, sans-serif',
                    animations: {
                        enabled: true,
                        easing: 'easeinout',
                        speed: 800,
                        animateGradually: {
                            enabled: true,
                            delay: 150
                        },
                        dynamicAnimation: {
                            enabled: true,
                            speed: 350
                        }
                    },
                    toolbar: {
                        show: true,
                        tools: {
                            download: true,
                            selection: false,
                            zoom: false,
                            zoomin: false,
                            zoomout: false,
                            pan: false,
                            reset: false
                        }
                    },
                    events: {
                        mouseMove: function(event, chartContext, config) {
                            // Add hover effects
                        }
                    }
                },
                colors: ['#5ad8ff', '#7cf5b1'],
                plotOptions: {
                    pie: {
                        startAngle: 0,
                        endAngle: 360,
                        expandOnClick: true,
                        offsetX: 0,
                        offsetY: 0,
                        customScale: 1,
                        dataLabels: {
                            offset: 0,
                            minAngleToShowLabel: 10
                        },
                        donut: {
                            size: '75%',
                            background: 'transparent',
                            labels: {
                                show: true,
                                name: { 
                                    show: true,
                                    fontSize: '16px',
                                    fontFamily: 'Inter, sans-serif',
                                    fontWeight: 600,
                                    color: undefined,
                                    offsetY: -10
                                },
                                value: { 
                                    show: true, 
                                    fontSize: '28px', 
                                    fontFamily: 'Inter, sans-serif',
                                    fontWeight: 700,
                                    color: undefined,
                                    offsetY: 10,
                                    formatter: function (val) {
                                        return val;
                                    }
                                },
                                total: {
                                    show: true,
                                    showAlways: true,
                                    label: 'Total Connections',
                                    fontSize: '14px',
                                    fontFamily: 'Inter, sans-serif',
                                    fontWeight: 500,
                                    color: '#9aa4c5',
                                    formatter: function(w) {
                                        return w.globals.seriesTotals.reduce((a, b) => a + b, 0);
                                    }
                                }
                            }
                        }
                    }
                },
                stroke: {
                    show: true,
                    width: 3,
                    colors: ['#0b0f1a']
                },
                legend: { 
                    position: 'bottom',
                    horizontalAlign: 'center',
                    floating: false,
                    fontSize: '14px',
                    fontFamily: 'Inter, sans-serif',
                    fontWeight: 500,
                    markers: {
                        width: 12,
                        height: 12,
                        strokeWidth: 0,
                        strokeColor: '#fff',
                        fillColors: undefined,
                        radius: 12,
                        customHTML: undefined,
                        onClick: undefined,
                        offsetX: 0,
                        offsetY: 0
                    },
                    itemMargin: {
                        horizontal: 10,
                        vertical: 5
                    }
                },
                dataLabels: { 
                    enabled: true,
                    enabledOnSeries: undefined,
                    textAnchor: 'middle',
                    distributed: false,
                    offsetX: 0,
                    offsetY: 0,
                    style: {
                        fontSize: '12px',
                        fontFamily: 'Inter, sans-serif',
                        fontWeight: 'bold',
                        colors: undefined
                    },
                    background: {
                        enabled: true,
                        foreColor: '#fff',
                        padding: 4,
                        borderRadius: 2,
                        borderWidth: 1,
                        borderColor: '#fff',
                        opacity: 0.9,
                        dropShadow: {
                            enabled: false,
                            top: 1,
                            left: 1,
                            blur: 1,
                            color: '#000',
                            opacity: 0.45
                        }
                    },
                    dropShadow: {
                        enabled: false,
                        top: 1,
                        left: 1,
                        blur: 1,
                        color: '#000',
                        opacity: 0.45
                    }
                },
                tooltip: {
                    enabled: true,
                    fixed: {
                        enabled: true,
                        position: 'topLeft',
                        offsetX: 0,
                        offsetY: 30,
                    },
                    x: {
                        show: true,
                        format: 'dd/MM/yy HH:mm'
                    },
                    y: {
                        formatter: function(value, { series, seriesIndex, dataPointIndex, w }) {
                            return value + ' connections (' + Math.round(value / w.globals.seriesTotals.reduce((a, b) => a + b, 0) * 100) + '%)';
                        },
                    },
                    marker: {
                        show: true,
                    },
                    items: {
                        display: 'flex',
                    },
                    style: {
                        fontSize: '12px',
                        fontFamily: undefined
                    }
                },
                responsive: [{
                    breakpoint: 480,
                    options: {
                        chart: {
                            width: 200
                        },
                        legend: {
                            position: 'bottom'
                        }
                    }
                }]
            });
            this.state.charts.connections.render();
        }

        // Countries Chart (Enhanced Bar with Gradient and Animations)
        if (this.el.countriesChart) {
            this.state.charts.countries = new ApexCharts(this.el.countriesChart, {
                series: [{ 
                    name: 'Connections', 
                    data: [],
                    color: undefined
                }],
                chart: {
                    type: 'bar',
                    height: 300,
                    fontFamily: 'Inter, sans-serif',
                    toolbar: { 
                        show: true,
                        tools: {
                            download: true,
                            selection: true,
                            zoom: true,
                            zoomin: true,
                            zoomout: true,
                            pan: true,
                            reset: true
                        }
                    },
                    animations: {
                        enabled: true,
                        easing: 'easeinout',
                        speed: 800,
                        animateGradually: {
                            enabled: true,
                            delay: 150
                        },
                        dynamicAnimation: {
                            enabled: true,
                            speed: 350
                        }
                    }
                },
                colors: ['#5ad8ff'],
                plotOptions: {
                    bar: {
                        horizontal: false,
                        borderRadius: 8,
                        borderRadiusApplication: 'end',
                        borderRadiusWhenStacked: 'last',
                        columnWidth: '65%',
                        barHeight: '70%',
                        distributed: false,
                        rangeBarOverlap: true,
                        rangeBarGroupRows: false,
                        hideZeroBarsWhenGrouped: false,
                        isDumbbell: false,
                        dumbbellColors: undefined,
                        isFunnel: false,
                        isFunnel3d: false,
                        dataLabels: {
                            position: 'top',
                        }
                    }
                },
                dataLabels: {
                    enabled: true,
                    enabledOnSeries: undefined,
                    formatter: function(val) {
                        return val;
                    },
                    textAnchor: 'middle',
                    distributed: false,
                    offsetX: 0,
                    offsetY: -20,
                    style: {
                        fontSize: '12px',
                        fontFamily: 'Inter, sans-serif',
                        fontWeight: 'bold',
                        colors: ['#e8ecff']
                    },
                    background: {
                        enabled: true,
                        foreColor: '#0b0f1a',
                        padding: 4,
                        borderRadius: 4,
                        borderWidth: 0,
                        borderColor: '#fff',
                        opacity: 0.9,
                        dropShadow: {
                            enabled: true,
                            top: 1,
                            left: 1,
                            blur: 2,
                            color: '#000',
                            opacity: 0.45
                        }
                    }
                },
                xaxis: {
                    categories: [],
                    labels: { 
                        style: { 
                            colors: '#9aa4c5',
                            fontSize: '12px',
                            fontFamily: 'Inter, sans-serif',
                            fontWeight: 400
                        },
                        rotate: -45,
                        rotateAlways: false,
                        hideOverlappingLabels: true,
                        showDuplicates: false,
                        trim: true,
                        minHeight: undefined,
                        maxHeight: 120,
                        floating: false,
                        offsetX: 0,
                        offsetY: 0,
                        formatter: undefined
                    },
                    axisBorder: {
                        show: true,
                        color: 'rgba(255,255,255,0.06)',
                        offsetX: 0,
                        offsetY: 0
                    },
                    axisTicks: {
                        show: true,
                        borderType: 'solid',
                        color: 'rgba(255,255,255,0.06)',
                        height: 6,
                        offsetX: 0,
                        offsetY: 0
                    }
                },
                yaxis: {
                    show: true,
                    showAlways: true,
                    showForNullSeries: true,
                    seriesName: undefined,
                    opposite: false,
                    reversed: false,
                    logarithmic: false,
                    logBase: 10,
                    tickAmount: 6,
                    forceNiceScale: false,
                    min: 0,
                    max: undefined,
                    floating: false,
                    decimalsInFloat: undefined,
                    labels: { 
                        show: true,
                        align: 'right',
                        minWidth: 0,
                        maxWidth: 160,
                        style: { 
                            colors: '#9aa4c5',
                            fontSize: '12px',
                            fontFamily: 'Inter, sans-serif',
                            fontWeight: 400,
                            cssClass: 'apexcharts-yaxis-label'
                        },
                        offsetX: 0,
                        offsetY: 0,
                        formatter: function(value) {
                            return value;
                        }
                    },
                    axisBorder: {
                        show: false,
                        color: '#78909C',
                        offsetX: 0,
                        offsetY: 0
                    },
                    axisTicks: {
                        show: false,
                        borderType: 'solid',
                        color: '#78909C',
                        width: 6,
                        offsetX: 0,
                        offsetY: 0
                    },
                    title: {
                        text: 'Connection Count',
                        rotate: -90,
                        offsetX: 0,
                        offsetY: 0,
                        style: {
                            color: '#e8ecff',
                            fontSize: '12px',
                            fontFamily: 'Inter, sans-serif',
                            fontWeight: 600
                        }
                    },
                    crosshairs: {
                        show: true,
                        position: 'back',
                        stroke: {
                            color: '#b6b6b6',
                            width: 1,
                            dashArray: 0
                        }
                    },
                    tooltip: {
                        enabled: true,
                        offsetX: 0
                    }
                },
                grid: {
                    show: true,
                    borderColor: 'rgba(255,255,255,0.06)',
                    strokeDashArray: 4,
                    position: 'back',
                    xaxis: {
                        lines: {
                            show: false
                        }
                    },
                    yaxis: {
                        lines: {
                            show: true
                        }
                    },
                    row: {
                        colors: undefined,
                        opacity: 0.5
                    },
                    column: {
                        colors: undefined,
                        opacity: 0.5
                    },
                    padding: {
                        top: 0,
                        right: 0,
                        bottom: 0,
                        left: 0
                    }
                },
                tooltip: {
                    enabled: true,
                    fixed: {
                        enabled: true,
                        position: 'topLeft',
                        offsetX: 0,
                        offsetY: 30
                    },
                    x: {
                        show: true
                    },
                    y: {
                        formatter: function(value, { series, seriesIndex, dataPointIndex, w }) {
                            return value + ' connections';
                        }
                    },
                    marker: {
                        show: true
                    },
                    items: {
                        display: 'flex'
                    },
                    style: {
                        fontSize: '12px',
                        fontFamily: 'Inter, sans-serif'
                    }
                },
                legend: {
                    show: true,
                    showForSingleSeries: false,
                    showForNullSeries: true,
                    showForZeroSeries: true,
                    position: 'top',
                    horizontalAlign: 'right',
                    floating: false,
                    fontSize: '14px',
                    fontFamily: 'Inter, sans-serif',
                    fontWeight: 400,
                    formatter: undefined,
                    inverseOrder: false,
                    width: undefined,
                    height: undefined,
                    tooltipHoverFormatter: undefined,
                    customLegendItems: [],
                    offsetX: 0,
                    offsetY: 0,
                    labels: {
                        colors: '#e8ecff',
                        useSeriesColors: false
                    },
                    markers: {
                        width: 12,
                        height: 12,
                        strokeWidth: 0,
                        strokeColor: '#fff',
                        fillColors: undefined,
                        radius: 12,
                        customHTML: undefined,
                        onClick: undefined,
                        offsetX: 0,
                        offsetY: 0
                    },
                    itemMargin: {
                        horizontal: 5,
                        vertical: 0
                    },
                    onItemClick: {
                        toggleDataSeries: true
                    },
                    onItemHover: {
                        highlightDataSeries: true
                    }
                },
                responsive: [{
                    breakpoint: 768,
                    options: {
                        chart: {
                            height: 250
                        },
                        plotOptions: {
                            bar: {
                                columnWidth: '70%'
                            }
                        }
                    }
                }, {
                    breakpoint: 480,
                    options: {
                        chart: {
                            height: 200
                        },
                        plotOptions: {
                            bar: {
                                columnWidth: '80%'
                            }
                        },
                        xaxis: {
                            labels: {
                                rotate: -45
                            }
                        }
                    }
                }]
            });
            this.state.charts.countries.render();
        }

        // Add additional chart types for enhanced visualization
        this.initAdditionalCharts();
    },

    // Initialize additional enhanced charts
    initAdditionalCharts() {
        // Response Time Heatmap (Optional)
        if (document.getElementById('responseTimeHeatmap')) {
            this.state.charts.responseTime = new ApexCharts(document.getElementById('responseTimeHeatmap'), {
                series: [{
                    name: 'Response Time (ms)',
                    data: []
                }],
                chart: {
                    height: 300,
                    type: 'heatmap',
                    toolbar: {
                        show: true
                    }
                },
                dataLabels: {
                    enabled: false
                },
                stroke: {
                    width: 1
                },
                xaxis: {
                    type: 'datetime',
                    labels: {
                        style: {
                            colors: '#9aa4c5'
                        }
                    }
                },
                yaxis: {
                    labels: {
                        style: {
                            colors: '#9aa4c5'
                        }
                    }
                },
                tooltip: {
                    x: {
                        format: 'dd/MM/yy HH:mm'
                    }
                },
                legend: {
                    position: 'top',
                    horizontalAlign: 'right'
                }
            });
            this.state.charts.responseTime.render();
        }

        // Traffic Distribution Radial Bar (Optional)
        if (document.getElementById('trafficDistribution')) {
            this.state.charts.traffic = new ApexCharts(document.getElementById('trafficDistribution'), {
                series: [],
                chart: {
                    height: 300,
                    type: 'radialBar',
                    toolbar: {
                        show: true
                    }
                },
                plotOptions: {
                    radialBar: {
                        startAngle: -135,
                        endAngle: 135,
                        dataLabels: {
                            name: {
                                fontSize: '16px',
                                color: undefined,
                                offsetY: 120
                            },
                            value: {
                                offsetY: 76,
                                fontSize: '22px',
                                color: undefined,
                                formatter: function (val) {
                                    return val + '%';
                                }
                            }
                        }
                    }
                },
                fill: {
                    type: 'gradient',
                    gradient: {
                        shade: 'dark',
                        shadeIntensity: 0.15,
                        inverseColors: false,
                        opacityFrom: 1,
                        opacityTo: 1,
                        stops: [0, 50, 65, 91]
                    }
                },
                stroke: {
                    dashArray: 4
                },
                labels: ['TCP', 'UDP', 'ICMP', 'Other']
            });
            this.state.charts.traffic.render();
        }
    },

    updateCharts(info) {
        const connections = info.connections || [];
        const tcp = connections.filter((c) => c.protocol === "TCP").length;
        const udp = connections.filter((c) => c.protocol === "UDP").length;

        const countries = (info.summary?.top_countries || [])
            .filter(([name]) => name)
            .slice(0, 5);

        // Update connection chart
        if (this.state.charts.connections) {
            this.state.charts.connections.updateSeries([tcp, udp]);
        }

        // Update countries chart
        if (this.state.charts.countries) {
            this.state.charts.countries.updateOptions({
                xaxis: { categories: countries.map(c => c[0]) }
            });
            this.state.charts.countries.updateSeries([{
                data: countries.map(c => c[1])
            }]);
        }
    },

    // Tabulator Table
    initConnectionsTable() {
        if (!this.el.connectionsTable) return;
        
        this.state.connectionsTable = new Tabulator(this.el.connectionsTable, {
            layout: "fitColumns",
            responsiveLayout: "hide",
            virtualDom: true,
            pagination: "local",
            paginationSize: 15,
            paginationSizeSelector: [10, 15, 25, 50],
            movableColumns: true,
            resizableColumns: true,
            placeholder: "No connections found",
            columns: [
                { 
                    title: "Protocol", 
                    field: "protocol", 
                    sorter: "string", 
                    width: 90,
                    headerFilter: false
                },
                { 
                    title: "Local Address", 
                    field: "local_addr", 
                    sorter: "string",
                    headerFilter: false
                },
                { 
                    title: "Remote Address", 
                    field: "remote_addr", 
                    sorter: "string",
                    headerFilter: false
                },
                { 
                    title: "Status", 
                    field: "status", 
                    sorter: "string",
                    headerFilter: "list",
                    headerFilterParams: { 
                        valuesLookup: true, 
                        clearable: true 
                    },
                    formatter: function(cell) {
                        const value = cell.getValue();
                        let className = '';
                        
                        switch(value.toLowerCase()) {
                            case 'established':
                                className = 'status-established';
                                break;
                            case 'time_wait':
                                className = 'status-time-wait';
                                break;
                            case 'fin_wait':
                            case 'fin_wait2':
                                className = 'status-fin-wait';
                                break;
                            default:
                                className = 'status-time-wait';
                        }
                        
                        return `<span class="status-badge ${className}">${value}</span>`;
                    }
                },
                { 
                    title: "Process", 
                    field: "process", 
                    sorter: "string",
                    headerFilter: "input"
                },
                { 
                    title: "Location", 
                    field: "location", 
                    sorter: "string",
                    headerFilter: "input"
                },
                { 
                    title: "Risk", 
                    field: "risk_level", 
                    sorter: "string",
                    width: 100,
                    formatter: function(cell) {
                        const value = cell.getValue();
                        const colors = {
                            info: '#5ad8ff',
                            warning: '#f7c948',
                            danger: '#ff6b81'
                        };
                        return `<span class="tabulator-text-uppercase" style="color: ${colors[value] || colors.info}; font-weight: 600;">${value.toUpperCase()}</span>`;
                    },
                    headerFilter: "list",
                    headerFilterParams: { 
                        values: { "info": "Info", "warning": "Warning", "danger": "Danger" },
                        clearable: true
                    }
                }
            ],
            rowFormatter: function(row) {
                const data = row.getData();
                if (data.risk_level === 'danger') {
                    row.getElement().style.backgroundColor = "rgba(255, 107, 129, 0.1)";
                } else if (data.risk_level === 'warning') {
                    row.getElement().style.backgroundColor = "rgba(247, 201, 72, 0.1)";
                }
            }
        });
    },

    // Security
    updateSecurity(security, connections) {
        const snapshot = JSON.stringify({
            score: security?.score,
            grade: security?.grade,
            warnings: security?.warnings,
            threats: security?.threats,
            secure: security?.secure,
            total: security?.total_connections,
        });
        if (snapshot === this.state.securitySnapshot) {
            // avoid redundant DOM work
        }
        this.state.securitySnapshot = snapshot;

        // Score + grade
        if (this.el.securityScore) {
            const score = security?.score ?? 0;
            this.el.securityScore.textContent = score;
            if (security?.grade) {
                this.el.securityScore.setAttribute("title", `Security grade: ${security.grade}`);
                this.el.securityScore.dataset.grade = security.grade;
            }
            gsap.from(this.el.securityScore, {
                scale: 0.5,
                opacity: 0,
                duration: 0.6,
                ease: "back.out(1.7)"
            });
        }

        // Status banner
        const dot = document.getElementById("security-status-dot");
        const label = document.getElementById("security-status-label");
        const sub = document.getElementById("security-status-sub");
        const badge = document.getElementById("security-grade");
        if (badge) badge.textContent = security?.grade ?? "N/A";
        if (label) label.textContent = security?.grade ?? "Unknown";
        if (sub) sub.textContent = security?.total_connections ? "Based on current active connections" : "Run a scan to assess";
        if (dot) {
            dot.className = "status-dot";
            if (security?.score >= 85) dot.classList.add("status-safe");
            else if (security?.score >= 70) dot.classList.add("status-warn");
            else dot.classList.add("status-risk");
        }

        // Metrics
        const setMetric = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val ?? "-";
        };
        setMetric("metric-threats", security?.threats);
        setMetric("metric-warnings", security?.warnings);
        setMetric("metric-secure", security?.secure);
        setMetric("metric-total", security?.total_connections);

        // Ribbon summary
        const ribbon = document.getElementById("security-ribbon");
        const ribbonText = document.getElementById("security-ribbon-text");
        if (ribbon && ribbonText) {
            ribbon.className = "status-ribbon";
            let text = "Run a scan to see your status";
            if (security?.score >= 85) {
                ribbon.classList.add("ribbon-safe");
                text = "System looks secure. Keep monitoring.";
            } else if (security?.score >= 70) {
                ribbon.classList.add("ribbon-warn");
                text = "Some warnings detected. Review connections.";
            } else {
                ribbon.classList.add("ribbon-risk");
                text = "Critical risks present. Act immediately.";
            }
            ribbonText.textContent = text;
        }

        // Recommendations
        const recosEl = document.getElementById("security-recos");
        if (recosEl) {
            recosEl.innerHTML = "";
            const recos = [];
            if ((security?.threats ?? 0) > 0) recos.push("Terminate high-risk connections shown below.");
            if ((security?.warnings ?? 0) > 2) recos.push("Review firewall rules and block unusual remote ports.");
            if ((security?.secure ?? 0) < 3) recos.push("Prefer secure protocols (HTTPS/SSH/IMAPS) for sensitive traffic.");
            if ((security?.suspicious_ports ?? 0) > 0) recos.push("Investigate services using uncommon ports.");
            if (!recos.length) recos.push("All clear. No urgent actions required.");
            recos.slice(0, 3).forEach((r) => {
                const li = document.createElement("li");
                li.textContent = r;
                recosEl.appendChild(li);
            });
        }

        // Findings list
        if (!this.el.securityList) return;
        this.el.securityList.innerHTML = "";
        
        if (!connections || connections.length === 0) {
            this.el.securityList.innerHTML =
                '<div class="finding-item info"><p>No connections to analyze yet.</p></div>';
            this.pushSecurityEvent("info", "Scan finished. No active connections to analyze.");
            return;
        }
        
        const riskyConnections = connections
            .filter((c) => c.risk_level !== "info")
            .sort((a, b) => (b.risk_level === "danger") - (a.risk_level === "danger"))
            .slice(0, 20);
            
        riskyConnections.forEach((c, index) => {
            const div = document.createElement("div");
            div.className = `finding-item ${c.risk_level}`;
            const iconClass = c.risk_level === "danger" ? "fa-exclamation-triangle" : "fa-exclamation-circle";
            div.innerHTML = `
                <i class="fas ${iconClass}"></i>
                <div class="finding-content">
                    <h4>${c.remote_addr || "Unknown remote"}</h4>
                    <p>${(c.risks || []).join("; ") || "Risk detected"}</p>
                </div>
            `;
            this.el.securityList.appendChild(div);
            
            gsap.from(div, {
                x: -30,
                opacity: 0,
                duration: 0.4,
                delay: index * 0.05,
                ease: "power2.out"
            });
        });
        
        if (!this.el.securityList.children.length) {
            this.el.securityList.innerHTML =
                '<div class="finding-item success"><p>No security risks detected.</p></div>';
        }

        // Security timeline event
        if ((security?.threats ?? 0) > 0) {
            this.pushSecurityEvent("danger", `${security.threats} threat(s) detected`);
        } else if ((security?.warnings ?? 0) > 0) {
            this.pushSecurityEvent("warning", `${security.warnings} warning connections detected`);
        } else {
            this.pushSecurityEvent("info", "Scan completed, no critical risks");
        }
    },

    pushSecurityEvent(level, text) {
        const entry = { level, text, at: new Date().toISOString() };
        this.state.securityTimeline.unshift(entry);
        this.state.securityTimeline = this.state.securityTimeline.slice(0, 15);
        this.renderSecurityTimeline();
    },

    renderSecurityTimeline() {
        const list = document.getElementById("security-timeline");
        if (!list) return;
        list.innerHTML = "";
        const fragment = document.createDocumentFragment();
        if (!this.state.securityTimeline.length) {
            const empty = document.createElement("div");
            empty.className = "timeline-item";
            empty.innerHTML = '<span class="timeline-dot info"></span><div class="timeline-text"><h4>No events yet</h4><p>Run a scan to populate timeline.</p></div><span class="timeline-time">-</span>';
            fragment.appendChild(empty);
        } else {
            this.state.securityTimeline.forEach((e) => {
                const div = document.createElement("div");
                div.className = "timeline-item";
                div.innerHTML = `
                    <span class="timeline-dot ${e.level}"></span>
                    <div class="timeline-text">
                        <h4>${e.text}</h4>
                        <p>${this.formatDate(e.at)}</p>
                    </div>
                    <span class="timeline-time">${this.formatTime(e.at)}</span>
                `;
                fragment.appendChild(div);
            });
        }
        list.appendChild(fragment);
    },

    // IP Lookup
    async lookupIp(ip) {
        this.setLoading(true);
        try {
            const data = await this.fetchJson("/api/lookup", { method: "POST", body: { ip } });
            if (!data?.success) throw new Error(data?.error || "Lookup failed");
            this.renderLookup(data);
            this.pushActivity(`Lookup for ${ip}`);
            this.saveHistoryEntry({ type: "lookup", ip, at: new Date().toISOString() });
            notyf.success(`Lookup complete for ${ip}`);
        } catch (err) {
            notyf.error(`Lookup error: ${err.message || err}`);
        } finally {
            this.setLoading(false);
        }
    },

    renderLookup(data) {
        if (this.el.lookupEmpty) this.el.lookupEmpty.style.display = "none";
        if (this.el.lookupResults) {
            this.el.lookupResults.style.display = "block";
            gsap.from(this.el.lookupResults, {
                y: 20,
                opacity: 0,
                duration: 0.4,
                ease: "power2.out"
            });
        }

        const geo = data.geolocation || {};
        const reverse = data.reverse_dns || {};

        this.el.resultFields.ip.textContent = data.ip || "-";
        this.el.resultFields.flag.textContent = this.countryFlag(geo.country_code);
        this.el.resultFields.country.textContent = geo.country || "-";
        this.el.resultFields.region.textContent = geo.region || "-";
        this.el.resultFields.city.textContent = geo.city || "-";
        this.el.resultFields.zip.textContent = geo.zip || "-";
        this.el.resultFields.coords.textContent =
            geo.lat && geo.lon ? `${geo.lat}, ${geo.lon}` : "Unavailable";
        this.el.resultFields.timezone.textContent = geo.timezone || "-";
        this.el.resultFields.isp.textContent = geo.isp || "-";
        this.el.resultFields.org.textContent = geo.org || "-";
        this.el.resultFields.asn.textContent = geo.asn || "-";
        this.el.resultFields.hostname.textContent = reverse.hostname || reverse.message || "-";

        this.renderMiniMap(geo);
        this.updateRecentIps(data.ip);
    },

    renderMiniMap(geo) {
        if (!this.el.miniMap || !geo.lat || !geo.lon || typeof L === "undefined") return;
        this.el.miniMap.innerHTML = "";
        const map = L.map(this.el.miniMap, { zoomControl: false }).setView([geo.lat, geo.lon], 4);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);
        L.marker([geo.lat, geo.lon]).addTo(map);
    },

    // Enhanced Map with Advanced Features
    initMap() {
        if (typeof L === "undefined" || !document.getElementById("map-container")) return;
            // Initialize map with enhanced options
        this.state.map = L.map("map-container", {
            preferCanvas: true,
            zoomControl: true,
            doubleClickZoom: true,
            scrollWheelZoom: true,
            dragging: true,
            tap: true,
            touchZoom: true,
            boxZoom: true,
            keyboard: true,
            attributionControl: false
        }).setView([20, 0], 2);
            
        // Enhanced Tile Providers with fallback options
        const tileProviders = [
            {
                name: 'CartoDB Voyager',
                url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
                attribution: 'OpenStreetMap contributors; CARTO',
                maxZoom: 19
            },
            {
                name: 'OpenTopoMap',
                url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
                attribution: 'Map data: OpenStreetMap contributors, SRTM | Style: OpenTopoMap (CC-BY-SA)',
                maxZoom: 17
            },
            {
                name: 'Esri World Imagery',
                url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attribution: 'Tiles © Esri and contributors',
                maxZoom: 19
            },
            {
                name: 'Stamen Toner',
                url: 'https://stamen-tiles-{s}.a.ssl.fastly.net/toner/{z}/{x}/{y}{r}.png',
                attribution: 'Map tiles by Stamen Design (CC BY 3.0); Map data © OpenStreetMap contributors',
                maxZoom: 20
            },
            {
                name: 'OpenStreetMap',
                url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                attribution: 'OpenStreetMap contributors',
                maxZoom: 19
            }
        ];
            
        // Add base layers control
        const baseLayers = {};
        tileProviders.forEach(provider => {
            baseLayers[provider.name] = L.tileLayer(provider.url, {
                attribution: provider.attribution,
                maxZoom: provider.maxZoom,
                tileSize: 256,
                updateWhenIdle: true,
                updateWhenZooming: false,
                updateInterval: 200,
                zIndex: 1,
                bounds: undefined,
                minZoom: 1,
                maxNativeZoom: provider.maxZoom,
                noWrap: false,
                pane: 'tilePane',
                className: '',
                keepBuffer: 2
            });
        });
            
        // Add default tile layer
        baseLayers['CartoDB Voyager'].addTo(this.state.map);
            
        // Add layer control
        L.control.layers(baseLayers, {}, {
            collapsed: true,
            position: 'topright',
            autoZIndex: true,
            hideSingleBase: false,
            sortLayers: false,
            sortFunction: undefined
        }).addTo(this.state.map);
            
        // Enhanced Marker Cluster with Advanced Options
        this.state.markerCluster = L.markerClusterGroup({
            chunkedLoading: true,
            chunkProgress: (processed, total, elapsed) => {
                // Progress callback for large datasets
                if (processed === total) {
                    console.log(`Loaded ${total} markers in ${elapsed}ms`);
                }
            },
            chunkDelay: 50,
            chunkInterval: 10,
            chunkProgressThrottle: 500,
                
            // Spiderfy options
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: true,
            zoomToBoundsOnClick: true,
            singleMarkerMode: false,
                
            // Clustering options
            maxClusterRadius: 80,
            disableClusteringAtZoom: 15,
                
            // Animation options
            animate: true,
            animateAddingMarkers: false,
            spiderfyDistanceMultiplier: 1,
            spiderLegPolylineOptions: { 
                weight: 1.5, 
                color: '#5ad8ff', 
                opacity: 0.5 
            },
                
            // Custom cluster icons
            iconCreateFunction: function(cluster) {
                const childCount = cluster.getChildCount();
                let size, fontSize, gradient;
                    
                if (childCount < 10) {
                    size = '30px';
                    fontSize = '12px';
                    gradient = 'linear-gradient(135deg, #5ad8ff, #7cf5b1)';
                } else if (childCount < 100) {
                    size = '40px';
                    fontSize = '14px';
                    gradient = 'linear-gradient(135deg, #f7c948, #f59e0b)';
                } else {
                    size = '50px';
                    fontSize = '16px';
                    gradient = 'linear-gradient(135deg, #ff6b81, #ef4444)';
                }
                    
                return L.divIcon({
                    html: `
                        <div style="
                            background: ${gradient}; 
                            color: #0a0d18; 
                            border-radius: 50%; 
                            width: ${size}; 
                            height: ${size}; 
                            display: flex; 
                            align-items: center; 
                            justify-content: center; 
                            font-weight: bold; 
                            font-size: ${fontSize};
                            border: 3px solid white; 
                            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                            transition: all 0.3s ease;
                        ">
                            ${childCount}
                        </div>
                    `,
                    className: 'enhanced-marker-cluster',
                    iconSize: L.point(parseInt(size), parseInt(size))
                });
            },
                
            // Polygon options
            polygonOptions: {
                fillColor: '#5ad8ff',
                color: '#5ad8ff',
                weight: 2,
                opacity: 0.6,
                fillOpacity: 0.2
            }
        });
            
        this.state.map.addLayer(this.state.markerCluster);
            
        // Add scale control
        L.control.scale({
            imperial: true,
            metric: true,
            position: 'bottomleft'
        }).addTo(this.state.map);
            
        // Add fullscreen control (if plugin available)
        if (L.Control.Fullscreen) {
            L.control.fullscreen({
                position: 'topleft',
                title: 'Show me the fullscreen !',
                titleCancel: 'Exit fullscreen mode',
                content: null,
                forceSeparateButton: true,
                forcePseudoFullscreen: true,
                fullscreenElement: false
            }).addTo(this.state.map);
        }
            
        // Add geolocation control
        L.control.locate({
            position: 'topleft',
            strings: {
                title: "Show me where I am",
                popup: "You are within {distance} {unit} from this point",
                outsideMapBoundsMsg: "You seem located outside the boundaries of the map"
            },
            locateOptions: {
                maxZoom: 16,
                watch: false,
                setView: true,
                timeout: 10000,
                enableHighAccuracy: false,
                maximumAge: 0,
                retainZoom: false
            }
        }).addTo(this.state.map);
            
        // Store map reference for external access
        window.ipCheckerMap = this.state.map;
        window.ipCheckerMarkerCluster = this.state.markerCluster;
    },

    async generateMap() {
        if (!this.state.map || !this.state.markerCluster) {
            notyf.warning("Map not ready");
            return;
        }
        const raw = this.el.mapTextarea?.value || "";
        const ips = raw
            .split(/\n|,/)
            .map((v) => v.trim())
            .filter(Boolean);
        if (!ips.length) {
            notyf.warning("Add at least one IP address");
            return;
        }
        this.setLoading(true);
        try {
            const res = await this.fetchJson("/api/bulk_lookup", { method: "POST", body: { ips } });
            this.clearMap();
            
            const markers = [];
            const geoData = [];
            
            (res.results || []).forEach((item) => {
                const geo = item.geolocation || {};
                if (geo.lat && geo.lon) {
                    // Enhanced marker with custom icon
                    const markerIcon = L.divIcon({
                        html: `
                            <div style="
                                background: linear-gradient(135deg, #5ad8ff, #7cf5b1); 
                                color: #0a0d18; 
                                border-radius: 50%; 
                                width: 24px; 
                                height: 24px; 
                                display: flex; 
                                align-items: center; 
                                justify-content: center; 
                                font-weight: bold; 
                                font-size: 10px;
                                border: 2px solid white; 
                                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                                transition: all 0.3s ease;
                            ">
                                <i class="fas fa-map-marker-alt"></i>
                            </div>
                        `,
                        className: 'enhanced-marker',
                        iconSize: L.point(24, 24),
                        iconAnchor: L.point(12, 24),
                        popupAnchor: L.point(0, -24)
                    });
                    
                    const marker = L.marker([geo.lat, geo.lon], {
                        icon: markerIcon,
                        title: `${item.ip} - ${geo.city || ''} ${geo.country || ''}`,
                        alt: item.ip,
                        riseOnHover: true,
                        riseOffset: 250
                    });
                    
                    // Enhanced popup with more information
                    const popupContent = `
                        <div style="min-width: 200px;">
                            <h3 style="margin: 0 0 10px 0; color: #5ad8ff; font-size: 16px;">${item.ip}</h3>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px;">
                                <div><strong>City:</strong> ${geo.city || 'N/A'}</div>
                                <div><strong>Country:</strong> ${geo.country || 'N/A'}</div>
                                <div><strong>Region:</strong> ${geo.region || 'N/A'}</div>
                                <div><strong>ISP:</strong> ${geo.isp || 'N/A'}</div>
                                <div><strong>Lat:</strong> ${geo.lat.toFixed(4)}</div>
                                <div><strong>Lon:</strong> ${geo.lon.toFixed(4)}</div>
                            </div>
                            <div style="font-size: 12px; color: #9aa4c5;">
                                <i class="fas fa-clock"></i> ${new Date().toLocaleString()}
                            </div>
                        </div>
                    `;
                    
                    marker.bindPopup(popupContent, {
                        maxWidth: 300,
                        className: 'enhanced-popup',
                        closeButton: true,
                        autoPan: true,
                        autoPanPadding: L.point(50, 50)
                    });
                    
                    // Add tooltip on hover
                    marker.bindTooltip(`${item.ip}<br>${geo.city || ''}`, {
                        permanent: false,
                        direction: 'top',
                        offset: L.point(0, -30),
                        opacity: 0.9
                    });
                    
                    markers.push(marker);
                    
                    // Store geo data for heatmap
                    geoData.push({
                        lat: geo.lat,
                        lng: geo.lon,
                        ip: item.ip,
                        city: geo.city,
                        country: geo.country,
                        isp: geo.isp
                    });
                }
            });
            
            if (markers.length) {
                // Add markers to cluster group
                this.state.markerCluster.addLayers(markers);
                
                // Fit bounds with padding
                const bounds = this.state.markerCluster.getBounds();
                if (bounds.isValid()) {
                    this.state.map.fitBounds(bounds, { 
                        padding: [50, 50],
                        maxZoom: 12
                    });
                }
                
                // Store geo data for potential heatmap
                this.state.geoData = geoData;
                
                // Success notification with statistics
                notyf.success(`Map updated with ${markers.length} locations`);
                
                // Add to map history
                if (!this.state.mapHistory) this.state.mapHistory = [];
                this.state.mapHistory.push({
                    timestamp: new Date(),
                    ipCount: ips.length,
                    locationCount: markers.length,
                    bounds: bounds
                });
                
                // Keep only last 10 history entries
                if (this.state.mapHistory.length > 10) {
                    this.state.mapHistory.shift();
                }
                
            } else {
                notyf.warning("No valid locations found");
            }
        } catch (err) {
            notyf.error(`Map error: ${err.message || err}`);
        } finally {
            this.setLoading(false);
        }
    },

    clearMap() {
        if (this.state.markerCluster) {
            this.state.markerCluster.clearLayers();
        }
    },

    // Reports
    async generateReport() {
        const params = new URLSearchParams({
            include_system: this.el.includeSystem?.checked ? "true" : "false",
            include_connections: this.el.includeConnections?.checked ? "true" : "false",
            include_security: this.el.includeSecurity?.checked ? "true" : "false",
            include_geolocation: this.el.includeGeolocation?.checked ? "true" : "false",
        });
        this.setLoading(true);
        try {
            const data = await this.fetchJson(`/api/report?${params.toString()}`);
            this.state.lastReport = data;
            this.renderReport(data);
            notyf.success("Report generated");
        } catch (err) {
            notyf.error(`Report error: ${err.message || err}`);
        } finally {
            this.setLoading(false);
        }
    },

    renderReport(data) {
        if (!this.el.reportResults) return;
        this.el.reportResults.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        if (this.el.exportButtons) this.el.exportButtons.style.display = "flex";
        
        gsap.from(this.el.reportResults, {
            y: 20,
            opacity: 0,
            duration: 0.4,
            ease: "power2.out"
        });
    },

    downloadReport() {
        if (!this.state.lastReport) {
            notyf.warning("Generate a report first");
            return;
        }
        const blob = new Blob([JSON.stringify(this.state.lastReport, null, 2)], {
            type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "ip-checker-report.json";
        a.click();
        URL.revokeObjectURL(url);
        notyf.success("Report downloaded");
    },

    // History
    renderHistory() {
        if (!this.el.historyList) return;
        this.el.historyList.innerHTML = "";
        if (!this.state.lookupHistory.length) {
            this.el.historyList.innerHTML =
                '<div class="empty-state"><i class="fas fa-history"></i><p>No history yet</p></div>';
            return;
        }
        this.state.lookupHistory.slice(-20).reverse().forEach((entry, index) => {
            const div = document.createElement("div");
            div.className = "history-item";
            div.innerHTML = `
                <div>
                    <strong>${entry.type === "lookup" ? entry.ip : "PC Investigation"}</strong>
                    <div class="small muted">${this.formatDate(entry.at)}</div>
                </div>
                ${
                    entry.type === "lookup"
                        ? `<button class="btn-chip" data-ip="${entry.ip}">Lookup</button>`
                        : ""
                }
            `;
            const btn = div.querySelector("button");
            if (btn) btn.addEventListener("click", () => this.lookupIp(entry.ip));
            this.el.historyList.appendChild(div);
            
            gsap.from(div, {
                x: -20,
                opacity: 0,
                duration: 0.3,
                delay: index * 0.03,
                ease: "power2.out"
            });
        });
    },

    saveHistoryEntry(entry) {
        this.state.lookupHistory.push(entry);
        this.state.lookupHistory = this.state.lookupHistory.slice(-40);
        localStorage.setItem("ipchecker-history", JSON.stringify(this.state.lookupHistory));
        this.renderHistory();
    },

    updateRecentIps(ip) {
        if (!ip || !this.el.recentIps) return;
        const unique = [ip, ...(this.state.lookupHistory.filter((h) => h.type === "lookup").map((h) => h.ip))];
        const deduped = [...new Set(unique)].slice(0, 6);
        this.el.recentIps.innerHTML = "";
        deduped.forEach((item) => {
            const btn = document.createElement("button");
            btn.className = "btn-chip";
            btn.textContent = item;
            btn.addEventListener("click", () => {
                if (this.el.ipInput) this.el.ipInput.value = item;
                this.lookupIp(item);
            });
            this.el.recentIps.appendChild(btn);
        });
    },

    pushActivity(text) {
        if (!this.el.activityList) return;
        const item = document.createElement("div");
        item.className = "activity-item";
        item.innerHTML = `
            <div class="activity-icon info"><i class="fas fa-info"></i></div>
            <div class="activity-content">
                <p>${text}</p>
                <span class="activity-time">Just now</span>
            </div>
        `;
        this.el.activityList.prepend(item);
        
        gsap.from(item, {
            x: -30,
            opacity: 0,
            duration: 0.4,
            ease: "power2.out"
        });
        
        while (this.el.activityList.children.length > 10) {
            this.el.activityList.removeChild(this.el.activityList.lastChild);
        }
    },

    // Utilities
    debounce(fn, wait = 300) {
        let t;
        return (...args) => {
            clearTimeout(t);
            t = setTimeout(() => fn.apply(this, args), wait);
        };
    },

    async fetchJson(url, options = {}) {
        const { method = "GET", body, timeout = 5000 } = options;
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeout);
        const res = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: body ? JSON.stringify(body) : undefined,
            signal: controller.signal,
            keepalive: false,
        }).finally(() => clearTimeout(timer));
        if (!res.ok) {
            const text = await res.text();
            const error = new Error(text || res.statusText);
            console.error(`[fetchJson] ${method} ${url} failed:`, error);
            throw error;
        }
        try {
            return await res.json();
        } catch (err) {
            console.error(`[fetchJson] Failed to parse JSON from ${url}:`, err);
            throw err;
        }
    },

    setLoading(show) {
        this.state.isLoading = show;
        if (this.el.loadingOverlay) this.el.loadingOverlay.style.display = show ? "flex" : "none";
    },

    formatGeo(geo) {
        if (!geo) return "-";
        const parts = [geo.city, geo.country].filter(Boolean);
        return parts.join(", ") || "-";
    },

    formatDate(iso) {
        if (!iso) return "-";
        try {
            return new Date(iso).toLocaleString();
        } catch {
            return iso;
        }
    },

    formatTime(iso) {
        try {
            return new Date(iso).toLocaleTimeString();
        } catch {
            return "-";
        }
    },

    countryFlag(code) {
        if (!code || code.length !== 2) return "";
        const pts = [...code.toUpperCase()].map((c) => 127397 + c.charCodeAt());
        return String.fromCodePoint(...pts);
    },

    safeLoadHistory() {
        try {
            const raw = localStorage.getItem("ipchecker-history");
            return raw ? JSON.parse(raw) : [];
        } catch (err) {
            console.warn("Failed to parse lookup history; resetting", err);
            localStorage.setItem("ipchecker-history", "[]");
            return [];
        }
    },

    exportInvestigation() {
        if (!this.state.investigation) {
            notyf.warning("Run a scan before exporting");
            return;
        }
        try {
            const blob = new Blob([JSON.stringify(this.state.investigation, null, 2)], {
                type: "application/json",
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "ip-investigation.json";
            a.click();
            URL.revokeObjectURL(url);
            notyf.success("Scan exported");
        } catch (err) {
            console.error("Export failed", err);
            notyf.error("Export failed");
        }
    },
    updateSecurityDashboard(security, info) {
        if (!security) return;
        
        // Calculate enhanced security metrics
        const threats = security.threats || 0;
        const warnings = security.warnings || 0;
        const secure = security.secure || 0;
        const total = info.summary?.total_connections || 0;
        const score = security.score || 0;
        
        // Determine security state for enhanced design
        const state = this.getSecurityState(score, threats, warnings);
        
        // Update security status header with enhanced design
        if (this.el.securityStatusHeader) {
            this.el.securityStatusHeader.className = `security-status-header ${state}`;
        }
        
        // Update security status icon with animation
        const statusIcon = document.querySelector('.security-status-icon');
        if (statusIcon) {
            statusIcon.className = `security-status-icon security-icon ${state}`;
        }
        
        // Update security score with color class
        if (this.el.securityScoreDisplay) {
            this.el.securityScoreDisplay.innerHTML = `${score}<span class="text-2xl">/100</span>`;
            this.el.securityScoreDisplay.className = `security-score-number ${state}`;
        }
        
        // Update security metrics with enhanced states
        this.updateEnhancedMetricCard('critical-threats', threats, threats > 0 ? 'critical' : 'good');
        this.updateEnhancedMetricCard('high-warnings', warnings, warnings > 2 ? 'high' : (warnings > 0 ? 'moderate' : 'good'));
        this.updateEnhancedMetricCard('secure-connections', secure, 'good');
        this.updateEnhancedMetricCard('total-connections', total, 'info');
        
        // Update legacy security metrics
        if (this.el.metricThreats) {
            this.animateCounter(this.el.metricThreats, threats);
        }
        if (this.el.metricWarnings) {
            this.animateCounter(this.el.metricWarnings, warnings);
        }
        if (this.el.metricSecure) {
            this.animateCounter(this.el.metricSecure, secure);
        }
        
        // Update security ribbon
        const ribbon = document.getElementById('security-ribbon');
        if (ribbon) {
            ribbon.className = `security-ribbon ${state}`;
        }
        
        // Update security timeline
        this.updateSecurityTimeline(threats, warnings, secure, total);
        
        // Integrate with EnhancedDesign system if available
        if (window.EnhancedDesign?.updateSecurityDashboard) {
            window.EnhancedDesign.updateSecurityDashboard({
                score, threats, warnings, secure, total_connections: total
            });
        }
        
        // Dispatch custom event for other modules
        window.dispatchEvent(new CustomEvent('app:security-update', {
            detail: {
                score,
                threats,
                warnings,
                secure,
                total,
                suspicious_ports: security.suspicious_ports || 0,
                geo_failures: security.geo_failures || 0,
                grade: security.grade,
                state
            }
        }));
    },
    
    getSecurityState(score, threats, warnings) {
        if (threats > 0) return 'critical';
        if (warnings > 3) return 'high';
        if (warnings > 0) return 'moderate';
        if (score >= 90) return 'excellent';
        if (score >= 75) return 'good';
        if (score >= 60) return 'moderate';
        if (score >= 40) return 'high';
        return 'critical';
    },
    
    updateEnhancedMetricCard(id, value, state) {
        const element = document.getElementById(id);
        if (!element) return;
        
        const card = element.closest('.security-metric-card');
        if (card) {
            // Update card state class
            card.classList.remove('critical', 'high', 'moderate', 'good', 'excellent', 'info');
            card.classList.add(state);
        }
        
        // Update value with animation
        const currentValue = parseInt(element.textContent) || 0;
        this.animateCounter(element, value);
        
        // Update value color class
        element.classList.remove('critical', 'high', 'moderate', 'good', 'excellent', 'info');
        element.classList.add(state);
    },
    
    getSecurityStatusConfig(score) {
        if (score >= 90) {
            return {
                class: 'excellent',
                title: 'EXCELLENT SECURITY',
                description: 'Strong security posture with minimal risks'
            };
        } else if (score >= 75) {
            return {
                class: 'good',
                title: 'GOOD SECURITY',
                description: 'Generally secure with minor improvements needed'
            };
        } else if (score >= 60) {
            return {
                class: 'moderate',
                title: 'MODERATE RISK',
                description: 'Some security concerns require attention'
            };
        } else if (score >= 40) {
            return {
                class: 'high',
                title: 'HIGH RISK',
                description: 'Significant vulnerabilities present'
            };
        } else {
            return {
                class: 'critical',
                title: 'CRITICAL RISK',
                description: 'Immediate system compromise likely'
            };
        }
    },
    
    updateMetricCard(cardElement, hasIssues) {
        if (!cardElement) return;
        
        // Remove existing animation classes
        cardElement.classList.remove('pulse', 'bounce');
        
        if (hasIssues) {
            cardElement.classList.add('security-icon', 'pulse');
        }
    },
    
    updateSecurityTimeline(threats, warnings, secure, total) {
        if (!this.el.securityTimeline) return;
            
        const events = [];
            
        // Add events based on current security state
        if (threats > 0) {
            events.push({
                type: 'critical',
                icon: 'fa-fire',
                title: `${threats} Critical Threat${threats > 1 ? 's' : ''} Detected`,
                time: 'Just now'
            });
        }
            
        if (warnings > 2) {
            events.push({
                type: 'warning',
                icon: 'fa-exclamation-triangle',
                title: 'Multiple Warnings Found',
                time: 'Recently'
            });
        }
            
        if (secure > total * 0.8) {
            events.push({
                type: 'info',
                icon: 'fa-check-circle',
                title: 'High Security Connections',
                time: 'Current'
            });
        }
            
        // Add default event if no issues
        if (events.length === 0) {
            events.push({
                type: 'info',
                icon: 'fa-shield-alt',
                title: 'System Scan Completed',
                time: 'Just now'
            });
        }
            
        // Update timeline display
        this.el.securityTimeline.innerHTML = events.map(event => `
            <div class="timeline-event ${event.type}">
                <div class="event-icon">
                    <i class="fas ${event.icon}"></i>
                </div>
                <div class="event-content">
                    <div class="event-title">${this.escapeHtml(event.title)}</div>
                    <div class="event-time">${event.time}</div>
                </div>
            </div>
        `).join('');
    },
};

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => App.init());

window.App = App;
