/**
 * Enhanced Security Dashboard Module
 * Provides real-time security status updates, automatic classification,
 * animated metric cards, and timeline event generation
 */

const SecurityDashboard = {
    // Configuration
    config: {
        updateInterval: 30000, // 30 seconds default refresh
        animationDuration: 600,
        timelineMaxEvents: 10,
        statusThresholds: {
            excellent: 90,
            good: 75,
            moderate: 60,
            high: 40
        }
    },

    // State
    state: {
        isPolling: false,
        pollTimer: null,
        lastUpdate: null,
        previousMetrics: {},
        timelineEvents: [],
        securityHistory: []
    },

    // DOM Element cache
    elements: {},

    /**
     * Initialize the security dashboard
     */
    init() {
        this.cacheElements();
        this.startRealTimeUpdates();
        this.initializeAnimations();
        this.setupEventListeners();
        console.log('[SecurityDashboard] Initialized');
    },

    /**
     * Cache DOM elements for performance
     */
    cacheElements() {
        this.elements = {
            // Status header elements
            statusHeader: document.getElementById('security-status-header'),
            statusTitle: document.querySelector('.security-status-title'),
            statusDescription: document.querySelector('.security-status-description'),
            scoreDisplay: document.querySelector('.security-score-number'),
            statusIcon: document.querySelector('.security-status-icon i'),

            // Metric cards
            threatsCard: document.querySelector('[data-priority="critical"]'),
            warningsCard: document.querySelector('[data-priority="high"]'),
            secureCard: document.querySelector('[data-priority="good"]'),
            totalCard: document.querySelector('[data-priority="info"]'),

            // Metric values
            threatsValue: document.getElementById('critical-threats'),
            warningsValue: document.getElementById('high-warnings'),
            secureValue: document.getElementById('secure-connections'),
            totalValue: document.getElementById('total-connections'),

            // Timeline
            timeline: document.getElementById('security-timeline'),

            // Connection status
            connectionStatus: document.querySelector('.connection-status'),
            statusDot: document.querySelector('.status-dot.online')
        };
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for visibility changes to pause/resume polling
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pausePolling();
            } else {
                this.resumePolling();
            }
        });

        // Listen for custom security update events
        window.addEventListener('security:updated', (e) => {
            this.handleSecurityUpdate(e.detail);
        });
        
        // Listen for app security updates from main.js
        window.addEventListener('app:security-update', (e) => {
            this.handleAppSecurityUpdate(e.detail);
        });
    },

    /**
     * Start real-time polling for security updates
     */
    startRealTimeUpdates() {
        if (this.state.isPolling) return;
        
        this.state.isPolling = true;
        this.performSecurityCheck();
        
        // Set up interval for polling
        this.state.pollTimer = setInterval(() => {
            this.performSecurityCheck();
        }, this.config.updateInterval);

        // Visual indicator that polling is active
        this.updatePollingIndicator(true);
    },

    /**
     * Pause polling when tab is not visible
     */
    pausePolling() {
        if (this.state.pollTimer) {
            clearInterval(this.state.pollTimer);
            this.state.pollTimer = null;
        }
        this.updatePollingIndicator(false);
    },

    /**
     * Resume polling when tab becomes visible
     */
    resumePolling() {
        if (!this.state.pollTimer && this.state.isPolling) {
            // Immediate check on resume
            this.performSecurityCheck();
            
            this.state.pollTimer = setInterval(() => {
                this.performSecurityCheck();
            }, this.config.updateInterval);
        }
        this.updatePollingIndicator(true);
    },

    /**
     * Stop real-time updates
     */
    stopRealTimeUpdates() {
        this.state.isPolling = false;
        if (this.state.pollTimer) {
            clearInterval(this.state.pollTimer);
            this.state.pollTimer = null;
        }
        this.updatePollingIndicator(false);
    },

    /**
     * Update visual indicator for polling status
     */
    updatePollingIndicator(active) {
        if (this.elements.statusDot) {
            if (active) {
                this.elements.statusDot.classList.add('online');
                this.elements.statusDot.style.animation = 'pulse 2s infinite';
            } else {
                this.elements.statusDot.classList.remove('online');
                this.elements.statusDot.style.animation = 'none';
            }
        }
    },

    /**
     * Perform security check via API
     */
    async performSecurityCheck() {
        try {
            const response = await fetch('/api/security/scan');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            this.processSecurityData(data);
            
        } catch (error) {
            console.error('[SecurityDashboard] Security check failed:', error);
            this.addTimelineEvent({
                type: 'error',
                title: 'Connection Lost',
                description: 'Unable to retrieve security status',
                time: new Date()
            });
        }
    },

    /**
     * Process security data and update UI
     */
    processSecurityData(data) {
        const previous = { ...this.state.previousMetrics };
        const current = {
            score: data.score || 0,
            threats: data.summary?.threats || 0,
            warnings: data.summary?.warnings || 0,
            secure: data.summary?.secure || 0,
            total: data.summary?.total_connections || 0,
            suspiciousPorts: data.summary?.suspicious_ports || 0,
            geoFailures: data.summary?.geo_failures || 0
        };

        // Check for changes and generate events
        this.detectSecurityChanges(previous, current);

        // Update state
        this.state.previousMetrics = current;
        this.state.lastUpdate = new Date();
        this.state.securityHistory.push({ ...current, timestamp: new Date() });

        // Keep only last 50 entries
        if (this.state.securityHistory.length > 50) {
            this.state.securityHistory.shift();
        }

        // Update UI
        this.updateSecurityDisplay(current, data.findings);

        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('security:updated', { 
            detail: { current, previous, findings: data.findings }
        }));
    },

    /**
     * Detect security changes and generate timeline events
     */
    detectSecurityChanges(previous, current) {
        // New threats detected
        if (current.threats > (previous.threats || 0)) {
            const diff = current.threats - (previous.threats || 0);
            this.addTimelineEvent({
                type: 'critical',
                title: `${diff} New Threat${diff > 1 ? 's' : ''} Detected`,
                description: `Total active threats: ${current.threats}`,
                time: new Date(),
                priority: 'high'
            });
            this.triggerAlert('threat');
        }

        // Threats resolved
        if (current.threats < (previous.threats || 0)) {
            this.addTimelineEvent({
                type: 'info',
                title: 'Threats Resolved',
                description: `${(previous.threats || 0) - current.threats} threat(s) no longer active`,
                time: new Date()
            });
        }

        // Warning threshold crossed
        if (current.warnings > 3 && (previous.warnings || 0) <= 3) {
            this.addTimelineEvent({
                type: 'warning',
                title: 'Multiple Warnings',
                description: `${current.warnings} active warnings require attention`,
                time: new Date(),
                priority: 'medium'
            });
        }

        // Score changes
        if (current.score < (previous.score || 100) - 10) {
            this.addTimelineEvent({
                type: 'warning',
                title: 'Security Score Dropped',
                description: `Score decreased by ${(previous.score || 100) - current.score} points`,
                time: new Date(),
                priority: 'medium'
            });
        } else if (current.score > (previous.score || 0) + 10) {
            this.addTimelineEvent({
                type: 'info',
                title: 'Security Score Improved',
                description: `Score increased by ${current.score - (previous.score || 0)} points`,
                time: new Date()
            });
        }

        // Secure connections milestone
        if (current.secure > (previous.secure || 0) + 5) {
            this.addTimelineEvent({
                type: 'info',
                title: 'Secure Connections Increased',
                description: `${current.secure} secure connections active`,
                time: new Date()
            });
        }

        // Suspicious port activity
        if (current.suspiciousPorts > (previous.suspiciousPorts || 0)) {
            this.addTimelineEvent({
                type: 'warning',
                title: 'Suspicious Port Activity',
                description: `Detected on ${current.suspiciousPorts} port(s)`,
                time: new Date(),
                priority: 'high'
            });
        }
    },

    /**
     * Update security display with current metrics
     */
    updateSecurityDisplay(metrics, findings = []) {
        // Classify security level
        const classification = this.classifySecurityLevel(metrics.score);
        
        // Update status header
        this.updateStatusHeader(classification, metrics.score);

        // Update metric cards with animations
        this.updateMetricCards(metrics);

        // Update timeline
        this.renderTimeline();

        // Update metric card animations based on priority
        this.animatePriorityCards(metrics);
    },

    /**
     * Classify security level based on score
     */
    classifySecurityLevel(score) {
        const { statusThresholds } = this.config;
        
        if (score >= statusThresholds.excellent) {
            return {
                level: 'excellent',
                class: 'excellent',
                title: 'EXCELLENT SECURITY',
                description: 'Strong security posture with minimal risks',
                icon: 'fa-shield-alt',
                color: '#2196f3'
            };
        } else if (score >= statusThresholds.good) {
            return {
                level: 'good',
                class: 'good',
                title: 'GOOD SECURITY',
                description: 'Generally secure with minor improvements needed',
                icon: 'fa-shield-alt',
                color: '#4caf50'
            };
        } else if (score >= statusThresholds.moderate) {
            return {
                level: 'moderate',
                class: 'moderate',
                title: 'MODERATE RISK',
                description: 'Some security concerns require attention',
                icon: 'fa-exclamation-triangle',
                color: '#ffcc00'
            };
        } else if (score >= statusThresholds.high) {
            return {
                level: 'high',
                class: 'high',
                title: 'HIGH RISK',
                description: 'Significant vulnerabilities present',
                icon: 'fa-exclamation-triangle',
                color: '#ff8800'
            };
        } else {
            return {
                level: 'critical',
                class: 'critical',
                title: 'CRITICAL RISK',
                description: 'Immediate system compromise likely',
                icon: 'fa-radiation',
                color: '#ff4444'
            };
        }
    },

    /**
     * Update status header with classification
     */
    updateStatusHeader(classification, score) {
        const { statusHeader, statusTitle, statusDescription, scoreDisplay, statusIcon } = this.elements;

        if (statusHeader) {
            // Remove old classes
            statusHeader.classList.remove('excellent', 'good', 'moderate', 'high', 'critical');
            // Add new class
            statusHeader.classList.add(classification.class);
            
            // Animate transition
            gsap.fromTo(statusHeader, 
                { opacity: 0.7, scale: 0.98 },
                { opacity: 1, scale: 1, duration: 0.4, ease: 'power2.out' }
            );
        }

        if (statusTitle) {
            statusTitle.textContent = classification.title;
            gsap.from(statusTitle, {
                y: -10,
                opacity: 0,
                duration: 0.3,
                ease: 'power2.out'
            });
        }

        if (statusDescription) {
            statusDescription.textContent = classification.description;
        }

        if (scoreDisplay) {
            const oldScore = parseInt(scoreDisplay.textContent) || 0;
            this.animateCounter(scoreDisplay, oldScore, score);
        }

        if (statusIcon) {
            statusIcon.className = `fas ${classification.icon} security-icon ${classification.level === 'critical' ? 'pulse' : 'rotate'}`;
        }
    },

    /**
     * Update metric cards with values
     */
    updateMetricCards(metrics) {
        const { threatsValue, warningsValue, secureValue, totalValue } = this.elements;

        if (threatsValue) {
            const oldValue = parseInt(threatsValue.textContent) || 0;
            this.animateCounter(threatsValue, oldValue, metrics.threats);
        }

        if (warningsValue) {
            const oldValue = parseInt(warningsValue.textContent) || 0;
            this.animateCounter(warningsValue, oldValue, metrics.warnings);
        }

        if (secureValue) {
            const oldValue = parseInt(secureValue.textContent) || 0;
            this.animateCounter(secureValue, oldValue, metrics.secure);
        }

        if (totalValue) {
            const oldValue = parseInt(totalValue.textContent) || 0;
            this.animateCounter(totalValue, oldValue, metrics.total);
        }
    },

    /**
     * Animate metric cards that require attention
     */
    animatePriorityCards(metrics) {
        const { threatsCard, warningsCard, secureCard } = this.elements;

        // Threats card - critical priority
        if (threatsCard && metrics.threats > 0) {
            threatsCard.classList.add('attention-required');
            this.addCardAnimation(threatsCard, 'critical');
        } else if (threatsCard) {
            threatsCard.classList.remove('attention-required');
            this.removeCardAnimation(threatsCard);
        }

        // Warnings card - high priority
        if (warningsCard && metrics.warnings > 2) {
            warningsCard.classList.add('attention-required');
            this.addCardAnimation(warningsCard, 'warning');
        } else if (warningsCard) {
            warningsCard.classList.remove('attention-required');
            this.removeCardAnimation(warningsCard);
        }

        // Secure card - good status
        if (secureCard && metrics.secure > 10) {
            this.addCardAnimation(secureCard, 'success');
        } else if (secureCard) {
            this.removeCardAnimation(secureCard);
        }
    },

    /**
     * Add animation to metric card
     */
    addCardAnimation(card, type) {
        const animations = {
            critical: {
                boxShadow: '0 0 20px rgba(255, 68, 68, 0.5), 0 0 40px rgba(255, 68, 68, 0.3)',
                borderColor: 'var(--security-critical)',
                scale: 1.02
            },
            warning: {
                boxShadow: '0 0 15px rgba(255, 136, 0, 0.4)',
                borderColor: 'var(--security-high)',
                scale: 1.01
            },
            success: {
                boxShadow: '0 0 10px rgba(76, 175, 80, 0.3)',
                borderColor: 'var(--security-good)'
            }
        };

        const config = animations[type];
        if (!config) return;

        gsap.to(card, {
            boxShadow: config.boxShadow,
            borderColor: config.borderColor,
            scale: config.scale || 1,
            duration: 0.5,
            ease: 'power2.out',
            yoyo: true,
            repeat: type === 'critical' ? -1 : 0,
            repeatDelay: 0.5
        });
    },

    /**
     * Remove animation from metric card
     */
    removeCardAnimation(card) {
        gsap.to(card, {
            boxShadow: 'var(--shadow-small)',
            borderColor: 'var(--border)',
            scale: 1,
            duration: 0.3,
            ease: 'power2.out'
        });
    },

    /**
     * Add event to timeline
     */
    addTimelineEvent(event) {
        // Add to beginning of array
        this.state.timelineEvents.unshift({
            ...event,
            id: Date.now() + Math.random()
        });

        // Keep only max events
        if (this.state.timelineEvents.length > this.config.timelineMaxEvents) {
            this.state.timelineEvents = this.state.timelineEvents.slice(0, this.config.timelineMaxEvents);
        }

        // Update display
        this.renderTimeline();
    },

    /**
     * Render timeline events
     */
    renderTimeline() {
        const { timeline } = this.elements;
        if (!timeline) return;

        const events = this.state.timelineEvents;
        
        if (events.length === 0) {
            timeline.innerHTML = `
                <div class="security-timeline-event info">
                    <div class="font-semibold">System Monitoring Active</div>
                    <div class="text-sm opacity-75">Waiting for events...</div>
                </div>
            `;
            return;
        }

        timeline.innerHTML = events.map((event, index) => `
            <div class="security-timeline-event ${event.type}" data-event-id="${event.id}">
                <div class="font-semibold">${this.escapeHtml(event.title)}</div>
                ${event.description ? `<div class="text-sm opacity-75">${this.escapeHtml(event.description)}</div>` : ''}
                <div class="text-xs opacity-50 mt-1">${this.formatTime(event.time)}</div>
            </div>
        `).join('');

        // Animate new events
        gsap.from('.security-timeline-event[data-event-id]:first-child', {
            x: -30,
            opacity: 0,
            duration: 0.4,
            ease: 'power2.out'
        });
    },

    /**
     * Trigger visual alert
     */
    triggerAlert(type) {
        const alertStyles = {
            threat: { color: '#ff4444', icon: 'fa-exclamation-circle' },
            warning: { color: '#ff8800', icon: 'fa-exclamation-triangle' },
            info: { color: '#4caf50', icon: 'fa-info-circle' }
        };

        const style = alertStyles[type] || alertStyles.info;

        // Create alert overlay
        const alert = document.createElement('div');
        alert.className = 'security-alert-overlay';
        alert.innerHTML = `<i class="fas ${style.icon}"></i>`;
        alert.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            background: ${style.color};
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            z-index: 9999;
            box-shadow: 0 4px 20px ${style.color}80;
        `;

        document.body.appendChild(alert);

        gsap.fromTo(alert,
            { scale: 0, rotation: -180 },
            { scale: 1, rotation: 0, duration: 0.5, ease: 'back.out(1.7)' }
        );

        gsap.to(alert, {
            opacity: 0,
            y: -20,
            duration: 0.3,
            delay: 2,
            ease: 'power2.in',
            onComplete: () => alert.remove()
        });
    },

    /**
     * Animate counter from old to new value
     */
    animateCounter(element, from, to) {
        const obj = { value: from };
        
        gsap.to(obj, {
            value: to,
            duration: 1,
            ease: 'power2.out',
            onUpdate: () => {
                element.textContent = Math.round(obj.value);
            }
        });

        // Add scale animation for emphasis
        gsap.fromTo(element,
            { scale: 1.2 },
            { scale: 1, duration: 0.5, ease: 'power2.out' }
        );
    },

    /**
     * Initialize animations
     */
    initializeAnimations() {
        // Add attention animation styles
        const style = document.createElement('style');
        style.textContent = `
            @keyframes attention-pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.02); }
            }
            
            .security-metric-card.attention-required {
                animation: attention-pulse 2s infinite;
            }

            .security-metric-card.attention-critical {
                border-color: var(--security-critical) !important;
                box-shadow: 0 0 20px rgba(255, 68, 68, 0.4) !important;
            }

            .security-metric-card.attention-warning {
                border-color: var(--security-high) !important;
                box-shadow: 0 0 15px rgba(255, 136, 0, 0.3) !important;
            }

            @keyframes status-pulse {
                0% { box-shadow: 0 0 0 0 rgba(124, 245, 177, 0.4); }
                70% { box-shadow: 0 0 0 10px rgba(124, 245, 177, 0); }
                100% { box-shadow: 0 0 0 0 rgba(124, 245, 177, 0); }
            }

            .status-dot.online {
                animation: status-pulse 2s infinite;
            }
        `;
        document.head.appendChild(style);
    },

    /**
     * Handle security update from external source
     */
    handleSecurityUpdate(data) {
        if (data.current) {
            this.updateSecurityDisplay(data.current, data.findings);
        }
    },

    /**
     * Handle security update from main app
     */
    handleAppSecurityUpdate(data) {
        if (data) {
            // Convert to expected format
            const metrics = {
                score: data.score,
                threats: data.threats,
                warnings: data.warnings,
                secure: data.secure,
                total: data.total,
                suspiciousPorts: data.suspicious_ports,
                geoFailures: data.geo_failures
            };
            
            const previous = { ...this.state.previousMetrics };
            
            // Detect changes and generate events
            this.detectSecurityChanges(previous, metrics);
            
            // Update state
            this.state.previousMetrics = metrics;
            this.state.lastUpdate = new Date();
            
            // Update UI
            this.updateSecurityDisplay(metrics, []);
            
            // Update last update time display
            const lastUpdateEl = document.getElementById('last-update');
            if (lastUpdateEl) {
                lastUpdateEl.textContent = 'Just now';
            }
        }
    },

    /**
     * Format time for display
     */
    formatTime(date) {
        if (!date) return 'Unknown';
        const d = new Date(date);
        const now = new Date();
        const diff = (now - d) / 1000; // seconds

        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return d.toLocaleDateString();
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Get security history
     */
    getSecurityHistory() {
        return this.state.securityHistory;
    },

    /**
     * Get current metrics
     */
    getCurrentMetrics() {
        return this.state.previousMetrics;
    },

    /**
     * Set update interval
     */
    setUpdateInterval(intervalMs) {
        this.config.updateInterval = intervalMs;
        if (this.state.isPolling) {
            this.stopRealTimeUpdates();
            this.startRealTimeUpdates();
        }
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    SecurityDashboard.init();
});

// Expose to global scope
window.SecurityDashboard = SecurityDashboard;
