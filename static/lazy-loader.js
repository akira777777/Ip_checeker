/**
 * Lazy Loader for external libraries
 * Improves initial page load performance
 */

window.lazyLoadScripts = {
    leaflet: false,
    apexcharts: false,
    tabulator: false,
    notyf: false
};

function loadScript(src, id) {
    return new Promise((resolve, reject) => {
        if (document.getElementById(id)) {
            resolve();
            return;
        }
        const script = document.createElement('script');
        script.src = src;
        script.id = id;
        script.async = true;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

function loadCSS(href, id) {
    return new Promise((resolve) => {
        if (document.getElementById(id)) {
            resolve();
            return;
        }
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        link.id = id;
        link.onload = resolve;
        document.head.appendChild(link);
    });
}

window.loadNotyf = function() {
    if (window.lazyLoadScripts.notyf) return Promise.resolve();
    window.lazyLoadScripts.notyf = true;
    return Promise.all([
        loadCSS('https://cdn.jsdelivr.net/npm/notyf@3.10.0/notyf.min.css', 'notyf-css'),
        loadScript('https://cdn.jsdelivr.net/npm/notyf@3.10.0/notyf.min.js', 'notyf-js')
    ]);
};

window.loadApexCharts = function() {
    if (window.lazyLoadScripts.apexcharts) return Promise.resolve();
    window.lazyLoadScripts.apexcharts = true;
    return loadScript('https://cdn.jsdelivr.net/npm/apexcharts', 'apexcharts-js');
};

window.loadLeaflet = function() {
    if (window.lazyLoadScripts.leaflet) return Promise.resolve();
    window.lazyLoadScripts.leaflet = true;
    return Promise.all([
        loadCSS('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', 'leaflet-css'),
        loadScript('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js', 'leaflet-js'),
        loadScript('https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js', 'leaflet-cluster-js')
    ]);
};

window.loadTabulator = function() {
    if (window.lazyLoadScripts.tabulator) return Promise.resolve();
    window.lazyLoadScripts.tabulator = true;
    return Promise.all([
        loadCSS('https://unpkg.com/tabulator-tables@5.5.0/dist/css/tabulator.min.css', 'tabulator-css'),
        loadScript('https://unpkg.com/tabulator-tables@5.5.0/dist/js/tabulator.min.js', 'tabulator-js')
    ]);
};
