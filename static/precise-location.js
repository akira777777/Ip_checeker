/**
 * Precise Location Detection Module
 * =================================
 * 
 * Комбинирует несколько методов для максимально точного определения местоположения:
 * 1. Browser Geolocation API (GPS/WiFi) - точность до метров
 * 2. IP Geolocation - точность до города
 * 3. Визуализация погрешности на карте
 */

class PreciseLocationDetector {
    constructor() {
        this.map = null;
        this.markers = {
            ip: null,
            browser: null,
            precise: null
        };
        this.circles = {
            accuracy: null,
            ipRange: null
        };
        this.layers = {};
    }

    /**
     * Получить точное местоположение через браузер (GPS/WiFi)
     * Точность: 5-20 метров (GPS) или 20-100 метров (WiFi)
     */
    async getBrowserLocation(options = {}) {
        const defaultOptions = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        };
        
        const settings = { ...defaultOptions, ...options };
        
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported by this browser'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        type: 'browser',
                        lat: position.coords.latitude,
                        lon: position.coords.longitude,
                        accuracy: position.coords.accuracy, // в метрах
                        altitude: position.coords.altitude,
                        altitudeAccuracy: position.coords.altitudeAccuracy,
                        heading: position.coords.heading,
                        speed: position.coords.speed,
                        timestamp: position.timestamp
                    });
                },
                (error) => {
                    let message = 'Unknown error';
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            message = 'User denied geolocation permission';
                            break;
                        case error.POSITION_UNAVAILABLE:
                            message = 'Location information unavailable';
                            break;
                        case error.TIMEOUT:
                            message = 'Location request timed out';
                            break;
                    }
                    reject(new Error(message));
                },
                settings
            );
        });
    }

    /**
     * Отслеживание местоположения в реальном времени
     */
    watchLocation(callback, options = {}) {
        if (!navigator.geolocation) {
            callback(new Error('Geolocation not supported'), null);
            return null;
        }

        const settings = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0,
            ...options
        };

        return navigator.geolocation.watchPosition(
            (position) => {
                callback(null, {
                    lat: position.coords.latitude,
                    lon: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    timestamp: position.timestamp
                });
            },
            (error) => {
                callback(error, null);
            },
            settings
        );
    }

    /**
     * Получить IP-геолокацию с сервера
     */
    async getIPLocation() {
        try {
            const response = await fetch('/api/myip/detailed');
            const data = await response.json();
            
            if (data.geolocation && data.geolocation.lat && data.geolocation.lon) {
                return {
                    type: 'ip',
                    lat: data.geolocation.lat,
                    lon: data.geolocation.lon,
                    accuracy: 1000, // IP геолокация обычно точна до 1-10 км
                    city: data.geolocation.city,
                    country: data.geolocation.country,
                    isp: data.geolocation.isp,
                    ip: data.client_ip,
                    source: 'ip-api'
                };
            }
            throw new Error('IP geolocation unavailable');
        } catch (error) {
            console.error('IP location error:', error);
            return null;
        }
    }

    /**
     * Получить все доступные местоположения
     */
    async getAllLocations() {
        const result = {
            ip: null,
            browser: null,
            recommendations: []
        };

        // Получаем IP-геолокацию
        try {
            result.ip = await this.getIPLocation();
        } catch (e) {
            console.warn('IP location failed:', e);
        }

        // Пробуем получить браузерную геолокацию
        try {
            result.browser = await this.getBrowserLocation();
        } catch (e) {
            console.warn('Browser location failed:', e);
            result.recommendations.push('Enable location access for precise positioning');
        }

        // Анализируем разницу
        if (result.ip && result.browser) {
            const distance = this.calculateDistance(
                result.ip.lat, result.ip.lon,
                result.browser.lat, result.browser.lon
            );
            result.distance = distance;

            if (distance > 50) {
                result.recommendations.push(`IP location differs by ${Math.round(distance)}km from actual position`);
            }
        }

        return result;
    }

    /**
     * Рассчитать расстояние между двумя точками (Haversine formula)
     */
    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Радиус Земли в км
        const dLat = this.deg2rad(lat2 - lat1);
        const dLon = this.deg2rad(lon2 - lon1);
        const a = 
            Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(this.deg2rad(lat1)) * Math.cos(this.deg2rad(lat2)) * 
            Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    deg2rad(deg) {
        return deg * (Math.PI/180);
    }

    /**
     * Инициализировать карту с визуализацией точности
     */
    async initMap(containerId, ipLocation = null) {
        if (!window.L) {
            throw new Error('Leaflet not loaded');
        }

        // Создаем карту
        const defaultLat = ipLocation ? ipLocation.lat : 0;
        const defaultLon = ipLocation ? ipLocation.lon : 0;
        const defaultZoom = ipLocation ? 13 : 2;

        this.map = L.map(containerId).setView([defaultLat, defaultLon], defaultZoom);

        // Добавляем слои
        this.layers.osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap',
            maxZoom: 19
        }).addTo(this.map);

        this.layers.satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: '© Esri',
            maxZoom: 19
        });

        // Добавляем контрол переключения слоев
        const baseMaps = {
            "OpenStreetMap": this.layers.osm,
            "Satellite": this.layers.satellite
        };
        L.control.layers(baseMaps).addTo(this.map);

        return this.map;
    }

    /**
     * Показать местоположение на карте с индикатором точности
     */
    showLocation(location, options = {}) {
        if (!this.map) return;

        const {
            color = '#3b82f6',
            fillColor = '#3b82f6',
            title = 'Location',
            showAccuracy = true
        } = options;

        // Создаем маркер
        const marker = L.circleMarker([location.lat, location.lon], {
            radius: 8,
            fillColor: fillColor,
            color: color,
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        }).addTo(this.map);

        // Добавляем popup
        let popupContent = `<b>${title}</b><br>`;
        popupContent += `Lat: ${location.lat.toFixed(6)}<br>`;
        popupContent += `Lon: ${location.lon.toFixed(6)}<br>`;
        
        if (location.accuracy) {
            popupContent += `Accuracy: ${Math.round(location.accuracy)}m<br>`;
        }
        if (location.city) {
            popupContent += `City: ${location.city}<br>`;
        }
        if (location.isp) {
            popupContent += `ISP: ${location.isp}<br>`;
        }
        
        marker.bindPopup(popupContent);

        // Добавляем круг точности
        let accuracyCircle = null;
        if (showAccuracy && location.accuracy) {
            // Конвертируем метры в градусы (приблизительно)
            const accuracyKm = location.accuracy / 1000;
            
            accuracyCircle = L.circle([location.lat, location.lon], {
                radius: location.accuracy, // в метрах
                fillColor: fillColor,
                color: color,
                weight: 1,
                opacity: 0.5,
                fillOpacity: 0.1
            }).addTo(this.map);

            // Добавляем легенду точности
            const accuracyLabel = L.marker([location.lat, location.lon], {
                icon: L.divIcon({
                    className: 'accuracy-label',
                    html: `<div style="background: ${color}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; white-space: nowrap;">±${Math.round(location.accuracy)}m</div>`,
                    iconSize: [60, 20],
                    iconAnchor: [30, -10]
                })
            }).addTo(this.map);
        }

        return { marker, accuracyCircle };
    }

    /**
     * Показать сравнение IP vs Browser локации
     */
    async showComparisonMap(containerId) {
        const locations = await this.getAllLocations();
        
        // Определяем центр карты
        let center = [0, 0];
        let zoom = 2;
        
        if (locations.browser) {
            center = [locations.browser.lat, locations.browser.lon];
            zoom = 15;
        } else if (locations.ip) {
            center = [locations.ip.lat, locations.ip.lon];
            zoom = 13;
        }

        this.map = L.map(containerId).setView(center, zoom);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap',
            maxZoom: 19
        }).addTo(this.map);

        // Показываем браузерную локацию (самая точная)
        if (locations.browser) {
            this.showLocation(locations.browser, {
                color: '#10b981',
                fillColor: '#10b981',
                title: '📍 Your Precise Location (Browser)',
                showAccuracy: true
            });
        }

        // Показываем IP локацию
        if (locations.ip) {
            this.showLocation(locations.ip, {
                color: '#ef4444',
                fillColor: '#ef4444',
                title: '🌐 IP Location Estimate',
                showAccuracy: true
            });

            // Линия между точками
            if (locations.browser) {
                L.polyline(
                    [
                        [locations.browser.lat, locations.browser.lon],
                        [locations.ip.lat, locations.ip.lon]
                    ],
                    {
                        color: '#f59e0b',
                        weight: 2,
                        opacity: 0.6,
                        dashArray: '5, 10'
                    }
                ).addTo(this.map);

                // Расстояние
                const midLat = (locations.browser.lat + locations.ip.lat) / 2;
                const midLon = (locations.browser.lon + locations.ip.lon) / 2;
                
                L.marker([midLat, midLon], {
                    icon: L.divIcon({
                        className: 'distance-label',
                        html: `<div style="background: #f59e0b; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">${Math.round(locations.distance)}km difference</div>`,
                        iconSize: [100, 20],
                        iconAnchor: [50, 0]
                    })
                }).addTo(this.map);
            }
        }

        // Добавляем легенду
        const legend = L.control({ position: 'bottomright' });
        legend.onAdd = function() {
            const div = L.DomUtil.create('div', 'info legend');
            div.style.background = 'rgba(16, 23, 42, 0.9)';
            div.style.padding = '10px';
            div.style.borderRadius = '8px';
            div.style.color = '#e2e8f0';
            div.innerHTML = `
                <h4 style="margin: 0 0 10px 0; color: #3b82f6;">Location Sources</h4>
                <div style="display: flex; align-items: center; margin: 5px 0;">
                    <span style="background: #10b981; width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 8px;"></span>
                    <span>Browser (GPS/WiFi)</span>
                </div>
                <div style="display: flex; align-items: center; margin: 5px 0;">
                    <span style="background: #ef4444; width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 8px;"></span>
                    <span>IP Geolocation</span>
                </div>
                <div style="margin-top: 10px; font-size: 11px; color: #64748b;">
                    Circles show accuracy radius
                </div>
            `;
            return div;
        };
        legend.addTo(this.map);

        return locations;
    }

    /**
     * Создать детальный отчет о местоположении
     */
    async generateLocationReport() {
        const locations = await this.getAllLocations();
        
        let report = {
            timestamp: new Date().toISOString(),
            locations: locations,
            accuracy: {
                browser: locations.browser ? this.getAccuracyLevel(locations.browser.accuracy) : 'unavailable',
                ip: locations.ip ? this.getAccuracyLevel(locations.ip.accuracy) : 'unavailable'
            },
            recommendations: locations.recommendations || []
        };

        // Добавляем рекомендации по точности
        if (locations.browser) {
            if (locations.browser.accuracy < 20) {
                report.recommendations.push('Excellent! GPS-level precision achieved.');
            } else if (locations.browser.accuracy < 100) {
                report.recommendations.push('Good accuracy - WiFi-based positioning.');
            } else {
                report.recommendations.push('Limited accuracy - check GPS signal or WiFi connection.');
            }
        }

        return report;
    }

    getAccuracyLevel(accuracyMeters) {
        if (accuracyMeters < 10) return { level: 'excellent', text: 'GPS precision (<10m)' };
        if (accuracyMeters < 50) return { level: 'good', text: 'WiFi precision (<50m)' };
        if (accuracyMeters < 200) return { level: 'fair', text: 'Cell tower precision (<200m)' };
        if (accuracyMeters < 1000) return { level: 'poor', text: 'Approximate (<1km)' };
        return { level: 'very_poor', text: 'Very approximate (>1km)' };
    }
}

// Экспорт для использования в других модулях
window.PreciseLocationDetector = PreciseLocationDetector;
