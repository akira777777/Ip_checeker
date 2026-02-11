// IP Checker Pro - Service Worker
// Implements caching strategies for offline capability and performance

const CACHE_NAME = 'ipchecker-v2.3.1';
const urlsToCache = [
    '/',
    '/static/style.css',
    '/static/enhanced-design.css',
    '/static/main_optimized.js',
    '/static/enhanced-design.js',
    '/static/lazy-loader.js',
    '/static/security-dashboard.js',
    '/static/vpn-check.js',
    '/static/precise-location.js',
    '/api/health'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
            .catch(err => {
                console.error('Failed to cache:', err);
            })
    );
});

// Fetch event - implement cache-first strategy with network fallback
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }

    // Skip requests to external domains
    const url = new URL(event.request.url);
    if (url.origin !== location.origin) {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Cache hit - return response
                if (response) {
                    // Refresh cache in background for critical endpoints
                    if (shouldRefreshCache(event.request.url)) {
                        refreshCacheInBackground(event.request);
                    }
                    return response;
                }

                // Cache miss - fetch from network
                return fetch(event.request)
                    .then(response => {
                        // Check if we received a valid response
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }

                        // Clone response for caching
                        const responseToCache = response.clone();

                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });

                        return response;
                    })
                    .catch(() => {
                        // Network failure - return offline page or cached fallback
                        if (event.request.headers.get('accept').includes('text/html')) {
                            return caches.match('/');
                        }
                        return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
                    });
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    const cacheWhitelist = [CACHE_NAME];

    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheWhitelist.indexOf(cacheName) === -1) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Message handling for cache management
self.addEventListener('message', event => {
    if (event.data.action === 'skipWaiting') {
        self.skipWaiting();
    } else if (event.data.action === 'clearCache') {
        caches.delete(CACHE_NAME)
            .then(() => {
                event.source.postMessage({ action: 'cacheCleared' });
            });
    } else if (event.data.action === 'refreshCache') {
        refreshAllCachedResources();
    }
});

// Helper functions
function shouldRefreshCache(url) {
    const criticalPaths = ['/api/health', '/api/investigate'];
    return criticalPaths.some(path => url.includes(path));
}

function refreshCacheInBackground(request) {
    fetch(request)
        .then(response => {
            if (response.ok) {
                caches.open(CACHE_NAME)
                    .then(cache => cache.put(request, response));
            }
        })
        .catch(err => console.log('Background refresh failed:', err));
}

function refreshAllCachedResources() {
    caches.open(CACHE_NAME)
        .then(cache => {
            return cache.keys().then(requests => {
                requests.forEach(request => {
                    refreshCacheInBackground(request);
                });
            });
        });
}

// Background sync for failed requests
self.addEventListener('sync', event => {
    if (event.tag === 'sync-requests') {
        event.waitUntil(syncPendingRequests());
    }
});

function syncPendingRequests() {
    // Implementation for syncing queued requests when connection is restored
    // This would typically involve IndexedDB to store pending requests
    return Promise.resolve();
}