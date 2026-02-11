/**
 * Performance Optimization Utilities for IP Checker Pro
 * Contains resource preloading, lazy loading, and optimization helpers
 */

class PerformanceOptimizer {
    constructor() {
        this.resourceHints = new Set();
        this.preloadedAssets = new Map();
        this.lazyLoadedModules = new Map();
        this.performanceMetrics = {
            firstPaint: 0,
            firstContentfulPaint: 0,
            largestContentfulPaint: 0,
            cumulativeLayoutShift: 0,
            firstInputDelay: 0
        };
        this.init();
    }

    init() {
        this.measureCoreVitals();
        this.setupResourcePreloading();
        this.optimizeImages();
        this.setupLazyLoading();
    }

    // Measure Core Web Vitals
    measureCoreVitals() {
        if ('PerformanceObserver' in window) {
            // Largest Contentful Paint
            const lcpObserver = new PerformanceObserver((entryList) => {
                const entries = entryList.getEntries();
                const lastEntry = entries[entries.length - 1];
                this.performanceMetrics.largestContentfulPaint = lastEntry.startTime;
            });
            lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });

            // Cumulative Layout Shift
            const clsObserver = new PerformanceObserver((entryList) => {
                let clsValue = 0;
                for (const entry of entryList.getEntries()) {
                    if (!entry.hadRecentInput) {
                        clsValue += entry.value;
                    }
                }
                this.performanceMetrics.cumulativeLayoutShift = clsValue;
            });
            clsObserver.observe({ entryTypes: ['layout-shift'] });

            // First Input Delay
            const fidObserver = new PerformanceObserver((entryList) => {
                const entries = entryList.getEntries();
                entries.forEach(entry => {
                    this.performanceMetrics.firstInputDelay = entry.processingStart - entry.startTime;
                });
            });
            fidObserver.observe({ entryTypes: ['first-input'] });
        }

        // First Paint and First Contentful Paint
        if (performance.getEntriesByType) {
            const paintEntries = performance.getEntriesByType('paint');
            paintEntries.forEach(entry => {
                if (entry.name === 'first-paint') {
                    this.performanceMetrics.firstPaint = entry.startTime;
                } else if (entry.name === 'first-contentful-paint') {
                    this.performanceMetrics.firstContentfulPaint = entry.startTime;
                }
            });
        }
    }

    // Setup resource preloading hints
    setupResourcePreloading() {
        // Preload critical resources
        this.preloadResource('/static/main_optimized.js', 'script');
        this.preloadResource('/static/enhanced-design.css', 'style');
        
        // Prefetch non-critical resources
        this.prefetchResource('/static/vpn-check.js');
        this.prefetchResource('/static/precise-location.js');
    }

    preloadResource(url, as) {
        if (this.preloadedAssets.has(url)) return;
        
        const link = document.createElement('link');
        link.rel = 'preload';
        link.href = url;
        link.as = as;
        link.crossOrigin = 'anonymous';
        
        document.head.appendChild(link);
        this.preloadedAssets.set(url, link);
    }

    prefetchResource(url) {
        if (this.preloadedAssets.has(url)) return;
        
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = url;
        
        document.head.appendChild(link);
        this.preloadedAssets.set(url, link);
    }

    // Optimize images with lazy loading and modern formats
    optimizeImages() {
        const images = document.querySelectorAll('img[data-src]');
        
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    }

    // Setup lazy loading for modules
    setupLazyLoading() {
        // Intersection Observer for lazy loading components
        this.componentObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const element = entry.target;
                    const moduleName = element.dataset.module;
                    
                    if (moduleName && !this.lazyLoadedModules.has(moduleName)) {
                        this.loadModule(moduleName, element);
                        this.componentObserver.unobserve(element);
                    }
                }
            });
        }, {
            rootMargin: '100px' // Load 100px before entering viewport
        });
    }

    async loadModule(moduleName, container) {
        try {
            this.lazyLoadedModules.set(moduleName, 'loading');
            
            switch (moduleName) {
                case 'charts':
                    await this.loadChartingLibrary();
                    break;
                case 'maps':
                    await this.loadMappingLibrary();
                    break;
                case 'tables':
                    await this.loadTableLibrary();
                    break;
            }
            
            this.lazyLoadedModules.set(moduleName, 'loaded');
            container.classList.add('module-loaded');
            
        } catch (error) {
            console.error(`Failed to load module ${moduleName}:`, error);
            this.lazyLoadedModules.set(moduleName, 'error');
        }
    }

    async loadChartingLibrary() {
        if (window.ApexCharts) return;
        
        await loadScript('https://cdn.jsdelivr.net/npm/apexcharts');
        console.log('Charting library loaded');
    }

    async loadMappingLibrary() {
        if (window.L) return;
        
        await Promise.all([
            loadCSS('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'),
            loadScript('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js')
        ]);
        console.log('Mapping library loaded');
    }

    async loadTableLibrary() {
        if (window.Tabulator) return;
        
        await Promise.all([
            loadCSS('https://unpkg.com/tabulator-tables@5.5.0/dist/css/tabulator.min.css'),
            loadScript('https://unpkg.com/tabulator-tables@5.5.0/dist/js/tabulator.min.js')
        ]);
        console.log('Table library loaded');
    }

    // Memory management utilities
    monitorMemoryUsage() {
        if ('memory' in performance) {
            const memoryInfo = performance.memory;
            const usageMB = Math.round(memoryInfo.usedJSHeapSize / 1048576);
            const limitMB = Math.round(memoryInfo.jsHeapSizeLimit / 1048576);
            
            if (usageMB > limitMB * 0.8) {
                console.warn(`High memory usage: ${usageMB}MB / ${limitMB}MB`);
                this.triggerGarbageCollection();
            }
        }
    }

    triggerGarbageCollection() {
        // Force garbage collection in development
        if (window.gc) {
            window.gc();
        }
        
        // Clear unused caches
        if ('caches' in window) {
            caches.keys().then(names => {
                names.forEach(name => {
                    if (name.startsWith('ipchecker-') && name !== CACHE_NAME) {
                        caches.delete(name);
                    }
                });
            });
        }
    }

    // Performance reporting
    getPerformanceReport() {
        return {
            ...this.performanceMetrics,
            memoryUsage: this.getMemoryUsage(),
            cacheStatus: this.getCacheStatus(),
            lazyModules: Object.fromEntries(this.lazyLoadedModules)
        };
    }

    getMemoryUsage() {
        if ('memory' in performance) {
            const mem = performance.memory;
            return {
                used: Math.round(mem.usedJSHeapSize / 1048576),
                total: Math.round(mem.totalJSHeapSize / 1048576),
                limit: Math.round(mem.jsHeapSizeLimit / 1048576)
            };
        }
        return null;
    }

    getCacheStatus() {
        if ('caches' in window) {
            return new Promise(resolve => {
                caches.keys().then(names => {
                    resolve({
                        cacheNames: names,
                        activeCache: CACHE_NAME
                    });
                });
            });
        }
        return Promise.resolve(null);
    }
}

// Utility functions
function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.async = true;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

function loadCSS(href) {
    return new Promise((resolve, reject) => {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        link.onload = resolve;
        link.onerror = reject;
        document.head.appendChild(link);
    });
}

// Initialize performance optimizer when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.perfOptimizer = new PerformanceOptimizer();
    
    // Register service worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('SW registered:', registration);
            })
            .catch(error => {
                console.log('SW registration failed:', error);
            });
    }
});