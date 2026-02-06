/**
 * Enhanced Visual Design JavaScript - IP Checker Pro
 * Handles security state animations, theme switching, and responsive behaviors
 */

(function() {
    'use strict';

    // ========================================
    // Security State Manager
    // ========================================
    const SecurityStateManager = {
        states: ['critical', 'high', 'moderate', 'good', 'excellent', 'info'],
        
        getStateFromScore(score) {
            if (score === undefined || score === null) return 'info';
            if (score >= 90) return 'excellent';
            if (score >= 75) return 'good';
            if (score >= 60) return 'moderate';
            if (score >= 40) return 'high';
            return 'critical';
        },
        
        getStateFromThreats(threats, warnings) {
            if (threats > 0) return 'critical';
            if (warnings > 3) return 'high';
            if (warnings > 0) return 'moderate';
            return 'excellent';
        },
        
        applyState(element, state) {
            if (!element) return;
            
            // Remove all state classes
            this.states.forEach(s => element.classList.remove(s));
            
            // Add new state class
            if (this.states.includes(state)) {
                element.classList.add(state);
            }
            
            // Trigger animation refresh
            this.refreshAnimations(element);
        },
        
        refreshAnimations(element) {
            // Force reflow to restart CSS animations
            element.style.animation = 'none';
            element.offsetHeight; // Trigger reflow
            element.style.animation = '';
        }
    };

    // ========================================
    // Security Icon Animator
    // ========================================
    const SecurityIconAnimator = {
        icons: new Map(),
        
        register(element, state) {
            if (!element) return;
            
            this.icons.set(element, { state, timestamp: Date.now() });
            this.updateIcon(element, state);
        },
        
        updateIcon(element, state) {
            // Remove all animation classes
            element.classList.remove('critical', 'high', 'moderate', 'good', 'excellent', 'info', 'rotating', 'pulse-ring');
            
            // Add state-specific animation
            element.classList.add(state);
            
            // Add special effects for critical/high states
            if (state === 'critical') {
                element.classList.add('pulse-ring');
            } else if (state === 'high') {
                element.classList.add('rotating');
            }
        },
        
        updateAll(newState) {
            this.icons.forEach((data, element) => {
                data.state = newState;
                this.updateIcon(element, newState);
            });
        }
    };

    // ========================================
    // Score Circle Animator
    // ========================================
    const ScoreCircleAnimator = {
        animate(element, targetScore, duration = 1500) {
            if (!element) return;
            
            const state = SecurityStateManager.getStateFromScore(targetScore);
            const startTime = Date.now();
            const startScore = 0;
            
            // Update state class
            SecurityStateManager.applyState(element, state);
            
            // Set CSS custom property for conic gradient
            element.style.setProperty('--score-percentage', `${targetScore}%`);
            
            // Animate the value
            const animate = () => {
                const elapsed = Date.now() - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Easing function (ease-out-cubic)
                const easeOut = 1 - Math.pow(1 - progress, 3);
                const currentScore = Math.round(startScore + (targetScore - startScore) * easeOut);
                
                // Update display value
                const valueElement = element.querySelector('.security-score-circle-value');
                if (valueElement) {
                    valueElement.textContent = currentScore;
                }
                
                if (progress < 1) {
                    requestAnimationFrame(animate);
                }
            };
            
            requestAnimationFrame(animate);
        }
    };

    // ========================================
    // Theme Manager
    // ========================================
    const ThemeManager = {
        currentTheme: 'dark',
        
        init() {
            // Check for saved theme preference
            const savedTheme = localStorage.getItem('ipchecker-theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            
            if (savedTheme) {
                this.setTheme(savedTheme);
            } else if (prefersDark) {
                this.setTheme('dark');
            } else {
                this.setTheme('light');
            }
            
            // Listen for system theme changes
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (!localStorage.getItem('ipchecker-theme')) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
        },
        
        setTheme(theme) {
            this.currentTheme = theme;
            
            if (theme === 'light') {
                document.body.classList.add('light-theme');
            } else {
                document.body.classList.remove('light-theme');
            }
            
            // Update theme toggle button icon
            const themeToggle = document.getElementById('theme-toggle');
            if (themeToggle) {
                const icon = themeToggle.querySelector('i');
                if (icon) {
                    icon.className = theme === 'light' ? 'fas fa-sun' : 'fas fa-moon';
                }
            }
            
            // Dispatch theme change event
            window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
        },
        
        toggle() {
            const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
            this.setTheme(newTheme);
            localStorage.setItem('ipchecker-theme', newTheme);
        }
    };

    // ========================================
    // Responsive Manager
    // ========================================
    const ResponsiveManager = {
        breakpoints: {
            mobile: 480,
            tablet: 768,
            desktop: 1024,
            wide: 1440
        },
        
        currentBreakpoint: '',
        
        init() {
            this.updateBreakpoint();
            
            window.addEventListener('resize', this.debounce(() => {
                this.updateBreakpoint();
            }, 250));
        },
        
        updateBreakpoint() {
            const width = window.innerWidth;
            let newBreakpoint;
            
            if (width < this.breakpoints.mobile) {
                newBreakpoint = 'mobile';
            } else if (width < this.breakpoints.tablet) {
                newBreakpoint = 'tablet';
            } else if (width < this.breakpoints.desktop) {
                newBreakpoint = 'desktop';
            } else if (width < this.breakpoints.wide) {
                newBreakpoint = 'wide';
            } else {
                newBreakpoint = 'ultrawide';
            }
            
            if (newBreakpoint !== this.currentBreakpoint) {
                this.currentBreakpoint = newBreakpoint;
                document.body.setAttribute('data-breakpoint', newBreakpoint);
                window.dispatchEvent(new CustomEvent('breakpointchange', { 
                    detail: { breakpoint: newBreakpoint } 
                }));
            }
        },
        
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        isMobile() {
            return this.currentBreakpoint === 'mobile';
        },
        
        isTablet() {
            return this.currentBreakpoint === 'tablet';
        },
        
        isTouchDevice() {
            return window.matchMedia('(pointer: coarse)').matches;
        }
    };

    // ========================================
    // Security Dashboard Updater
    // ========================================
    const SecurityDashboardUpdater = {
        update(securityData) {
            if (!securityData) return;
            
            const { score, threats, warnings, secure, total_connections } = securityData;
            const state = SecurityStateManager.getStateFromScore(score);
            
            // Update header
            const header = document.querySelector('.security-status-header');
            if (header) {
                SecurityStateManager.applyState(header, state);
                
                // Update title and description
                const title = header.querySelector('.security-status-title');
                const desc = header.querySelector('.security-status-description');
                
                if (title) {
                    title.textContent = this.getStateTitle(state);
                }
                if (desc) {
                    desc.textContent = this.getStateDescription(state);
                }
            }
            
            // Update icon
            const icon = document.querySelector('.security-status-icon i');
            if (icon) {
                SecurityIconAnimator.register(icon.parentElement, state);
            }
            
            // Update score display
            const scoreDisplay = document.querySelector('.security-score-number');
            if (scoreDisplay) {
                scoreDisplay.innerHTML = `${score}<span class="text-2xl">/100</span>`;
                scoreDisplay.className = `security-score-number ${state}`;
            }
            
            // Update metric cards
            this.updateMetricCard('critical-threats', threats || 0, 'critical');
            this.updateMetricCard('high-warnings', warnings || 0, warnings > 0 ? 'high' : 'good');
            this.updateMetricCard('secure-connections', secure || 0, 'good');
            this.updateMetricCard('total-connections', total_connections || 0, 'info');
            
            // Update timeline
            this.addTimelineEvent('System scan completed', state);
        },
        
        updateMetricCard(id, value, state) {
            const card = document.querySelector(`#${id}`)?.closest('.security-metric-card');
            if (card) {
                SecurityStateManager.applyState(card, state);
                const valueElement = card.querySelector('.security-metric-value');
                if (valueElement) {
                    // Animate counter
                    this.animateCounter(valueElement, parseInt(valueElement.textContent) || 0, value);
                    valueElement.className = `security-metric-value ${state}`;
                }
            }
        },
        
        animateCounter(element, from, to, duration = 1000) {
            const startTime = Date.now();
            
            const animate = () => {
                const elapsed = Date.now() - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const easeOut = 1 - Math.pow(1 - progress, 3);
                const current = Math.round(from + (to - from) * easeOut);
                
                element.textContent = current;
                
                if (progress < 1) {
                    requestAnimationFrame(animate);
                }
            };
            
            requestAnimationFrame(animate);
        },
        
        addTimelineEvent(message, state) {
            const timeline = document.querySelector('.security-timeline-events');
            if (!timeline) return;
            
            const event = document.createElement('div');
            event.className = `security-timeline-event ${state}`;
            event.innerHTML = `
                <div class="font-semibold">${message}</div>
                <div class="text-sm opacity-75">Just now</div>
            `;
            
            timeline.insertBefore(event, timeline.firstChild);
            
            // Limit to 5 events
            while (timeline.children.length > 5) {
                timeline.removeChild(timeline.lastChild);
            }
            
            // Animate in
            event.style.opacity = '0';
            event.style.transform = 'translateX(-20px)';
            requestAnimationFrame(() => {
                event.style.transition = 'all 0.3s ease';
                event.style.opacity = '1';
                event.style.transform = 'translateX(0)';
            });
        },
        
        getStateTitle(state) {
            const titles = {
                critical: 'CRITICAL THREATS DETECTED',
                high: 'HIGH RISK WARNING',
                moderate: 'MODERATE RISK',
                good: 'GOOD SECURITY',
                excellent: 'EXCELLENT SECURITY',
                info: 'SYSTEM INFO'
            };
            return titles[state] || 'UNKNOWN STATUS';
        },
        
        getStateDescription(state) {
            const descriptions = {
                critical: 'Immediate action required - threats detected',
                high: 'Review recommended - potential risks found',
                moderate: 'Some concerns identified - monitor closely',
                good: 'Security measures are working well',
                excellent: 'Strong security posture with minimal risks',
                info: 'System information displayed'
            };
            return descriptions[state] || '';
        }
    };

    // ========================================
    // Intersection Observer for Animations
    // ========================================
    const ScrollAnimationObserver = {
        observer: null,
        
        init() {
            this.observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animate-in');
                        this.observer.unobserve(entry.target);
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            });
            
            // Observe security elements
            document.querySelectorAll('.security-metric-card, .security-timeline-event').forEach(el => {
                this.observer.observe(el);
            });
        }
    };

    // ========================================
    // Initialize
    // ========================================
    function init() {
        ThemeManager.init();
        ResponsiveManager.init();
        ScrollAnimationObserver.init();
        
        // Bind theme toggle
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => ThemeManager.toggle());
        }
        
        // Expose to global scope for integration with main app
        window.EnhancedDesign = {
            SecurityStateManager,
            SecurityIconAnimator,
            ScoreCircleAnimator,
            ThemeManager,
            ResponsiveManager,
            SecurityDashboardUpdater,
            
            // Convenience methods
            updateSecurityDashboard: (data) => SecurityDashboardUpdater.update(data),
            setTheme: (theme) => ThemeManager.setTheme(theme),
            toggleTheme: () => ThemeManager.toggle()
        };
        
        console.log('[EnhancedDesign] Initialized');
    }

    // Run initialization
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
