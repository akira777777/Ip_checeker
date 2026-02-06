# Руководство по рефакторингу - IP Checker Pro

## Цели рефакторинга

1. Улучшить масштабируемость
2. Упростить тестирование
3. Следовать лучшим практикам Flask
4. Улучшить поддерживаемость кода

---

## 1. Структура проекта

### Текущая структура
```
Ip_checeker/
├── app.py
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── script.js
```

### Рекомендуемая структура (Application Factory Pattern)
```
ip_checker/
├── app/
│   ├── __init__.py              # Application factory
│   ├── config.py                # Configuration classes
│   ├── extensions.py            # Flask extensions
│   ├── api/
│   │   ├── __init__.py
│   │   ├── geolocation.py       # Geolocation endpoints
│   │   ├── network.py           # Network analysis endpoints
│   │   ├── security.py          # Security scan endpoints
│   │   └── reports.py           # Report endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── geo_service.py       # Geolocation logic
│   │   ├── net_service.py       # Network analysis logic
│   │   └── cache_service.py     # Caching logic
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py        # Input validation
│   │   └── security.py          # Security utilities
│   └── templates/
│       └── index.html
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_api/
│   │   ├── test_geolocation.py
│   │   ├── test_network.py
│   │   └── test_security.py
│   └── test_services/
│       ├── test_geo_service.py
│       └── test_net_service.py
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .env.example
├── .gitignore
├── config.py
├── run.py
└── wsgi.py
```

---

## 2. Application Factory Pattern

### app/__init__.py
```python
from flask import Flask
from flask_limiter import Limiter
from flask_talisman import Talisman
from .config import config_by_name
from .extensions import limiter, talisman

def create_app(config_name='development'):
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions
    limiter.init_app(app)
    talisman.init_app(app, force_https=app.config.get('FORCE_HTTPS', False))
    
    # Register blueprints
    from .api.geolocation import geo_bp
    from .api.network import net_bp
    from .api.security import sec_bp
    from .api.reports import report_bp
    
    app.register_blueprint(geo_bp, url_prefix='/api')
    app.register_blueprint(net_bp, url_prefix='/api')
    app.register_blueprint(sec_bp, url_prefix='/api')
    app.register_blueprint(report_bp, url_prefix='/api')
    
    # Register error handlers
    register_error_handlers(app)
    
    return app

def register_error_handlers(app):
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "Rate limit exceeded", "success": False}), 429
    
    @app.errorhandler(404)
    def not_found_handler(e):
        return jsonify({"error": "Endpoint not found", "success": False}), 404
```

### app/extensions.py
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

limiter = Limiter(key_func=get_remote_address)
talisman = Talisman()
```

### app/config.py
```python
import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    JSON_SORT_KEYS = False
    GEO_CACHE_TTL = int(os.environ.get('GEO_CACHE_TTL', 3600))
    GEO_LOOKUP_LIMIT = int(os.environ.get('GEO_LOOKUP_LIMIT', 15))
    LOCAL_ONLY = os.environ.get('LOCAL_ONLY', 'True').lower() == 'true'
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'False').lower() == 'true'
    
class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    
class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    FORCE_HTTPS = True
    
class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    GEO_LOOKUP_LIMIT = 5
    
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
```

---

## 3. Flask Blueprints

### app/api/geolocation.py
```python
from flask import Blueprint, jsonify, request
from flask_limiter import Limiter
from ..services.geo_service import get_ip_geolocation, validate_ip
from ..extensions import limiter

geo_bp = Blueprint('geolocation', __name__)

@geo_bp.route("/geolocation/<ip>", methods=["GET"])
@limiter.limit("60 per minute")
def geolocation(ip: str):
    """Get geolocation for specific IP."""
    if not validate_ip(ip):
        return jsonify({"error": "Invalid IP address", "success": False}), 400
    return jsonify(get_ip_geolocation(ip))

@geo_bp.route("/lookup", methods=["GET", "POST"])
@limiter.limit("60 per minute")
def lookup():
    """Comprehensive IP lookup."""
    from ..services.geo_service import get_whois_info
    from ..services.net_service import reverse_dns_lookup
    
    if request.method == "GET":
        ip = request.args.get("ip", "").strip()
    else:
        data = request.get_json(silent=True) or {}
        ip = (data.get("ip") or "").strip()
    
    if not ip:
        return jsonify({"error": "No IP provided", "success": False}), 400
    
    if not validate_ip(ip):
        return jsonify({"error": "Invalid IP address", "success": False}), 400
    
    return jsonify({
        "ip": ip,
        "geolocation": get_ip_geolocation(ip),
        "whois": get_whois_info(ip),
        "reverse_dns": reverse_dns_lookup(ip),
        "success": True,
    })

@geo_bp.route("/bulk_lookup", methods=["POST"])
@limiter.limit("10 per minute")
def bulk_lookup():
    """Bulk IP lookup."""
    data = request.get_json(silent=True) or {}
    ips = [ip.strip() for ip in data.get("ips", []) if ip.strip()]
    
    if not ips:
        return jsonify({"error": "No IPs provided", "success": False}), 400
    
    if len(ips) > 50:
        return jsonify({"error": "Too many IPs (max 50)", "success": False}), 400
    
    from ..services.net_service import reverse_dns_lookup
    
    lookups = []
    for ip in ips:
        if validate_ip(ip):
            lookups.append({
                "ip": ip,
                "geolocation": get_ip_geolocation(ip),
                "reverse_dns": reverse_dns_lookup(ip),
            })
    
    return jsonify({"success": True, "results": lookups})
```

---

## 4. Service Layer

### app/services/geo_service.py
```python
import ipaddress
import logging
from time import time
from typing import Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logger = logging.getLogger(__name__)

GEO_CACHE: Dict[str, tuple[float, dict]] = {}
GEO_CACHE_TTL = 3600
GEO_API_URL = "https://ip-api.com/json/{ip}?fields=status,message,continent,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"

try:
    import ipapi
except ImportError:
    ipapi = None

try:
    import whois as whois_lib
except ImportError:
    whois_lib = None

class RetryableSession:
    """Session with retry logic."""
    
    def __init__(self):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
    
    def get(self, url: str, timeout: int = 5) -> requests.Response:
        return self.session.get(url, timeout=timeout)

retry_session = RetryableSession()


def validate_ip(ip: str) -> bool:
    """Validate IP address."""
    if not ip or not isinstance(ip, str):
        return False
    try:
        ipaddress.ip_address(ip.strip())
        return True
    except ValueError:
        return False


def is_private_ip(ip: str) -> bool:
    """Check if IP is private."""
    try:
        addr = ipaddress.ip_address(ip.strip())
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


def get_ip_geolocation(ip_address: str) -> dict:
    """Get geolocation with caching."""
    if not validate_ip(ip_address):
        return {"ip": ip_address, "status": "error", "message": "Invalid IP address"}
    
    now = time()
    cached = GEO_CACHE.get(ip_address)
    if cached and now - cached[0] < GEO_CACHE_TTL:
        return cached[1]
    
    # Try ipapi.co first
    if ipapi:
        try:
            location = ipapi.location(ip_address)
            if location and "error" not in location:
                data = {
                    "ip": ip_address,
                    "city": location.get("city"),
                    "region": location.get("region"),
                    "country": location.get("country_name") or location.get("country"),
                    "country_code": location.get("country_code"),
                    "lat": location.get("latitude"),
                    "lon": location.get("longitude"),
                    "timezone": location.get("timezone"),
                    "isp": location.get("org"),
                    "asn": location.get("asn"),
                    "status": "success",
                }
                GEO_CACHE[ip_address] = (now, data)
                return data
        except Exception as e:
            logger.warning(f"ipapi.co failed: {e}")
    
    # Fallback to ip-api.com
    try:
        resp = retry_session.get(GEO_API_URL.format(ip=ip_address), timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("status") == "success":
            result = {
                "ip": ip_address,
                "city": data.get("city"),
                "region": data.get("regionName"),
                "country": data.get("country"),
                "country_code": data.get("countryCode"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "timezone": data.get("timezone"),
                "isp": data.get("isp"),
                "asn": data.get("as"),
                "org": data.get("org"),
                "status": "success",
            }
            GEO_CACHE[ip_address] = (now, result)
            return result
        else:
            result = {
                "ip": ip_address,
                "status": data.get("status", "fail"),
                "message": data.get("message", "Unknown error")
            }
            GEO_CACHE[ip_address] = (now - GEO_CACHE_TTL + 300, result)
            return result
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"ip": ip_address, "status": "error", "message": "Service temporarily unavailable"}


def get_whois_info(ip_address: str) -> dict:
    """Get WHOIS information."""
    if not validate_ip(ip_address):
        return {"status": "error", "message": "Invalid IP address"}
    
    if not whois_lib:
        return {"status": "unavailable", "message": "python-whois not installed"}
    
    try:
        w = whois_lib.whois(ip_address)
        return {
            "status": "success",
            "domain": w.domain_name,
            "registrar": w.registrar,
            "creation_date": str(w.creation_date) if w.creation_date else None,
            "expiration_date": str(w.expiration_date) if w.expiration_date else None,
            "name_servers": w.name_servers,
            "status_raw": w.status,
        }
    except Exception as e:
        logger.warning(f"WHOIS lookup failed: {e}")
        return {"status": "error", "message": "WHOIS lookup failed"}
```

---

## 5. Тестирование

### tests/conftest.py
```python
import pytest
from app import create_app

@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()
```

### tests/test_api/test_geolocation.py
```python
import pytest
from unittest.mock import patch, MagicMock

def test_geolocation_success(client):
    """Test successful geolocation lookup."""
    with patch('app.services.geo_service.get_ip_geolocation') as mock_geo:
        mock_geo.return_value = {
            "ip": "8.8.8.8",
            "city": "Mountain View",
            "status": "success"
        }
        response = client.get('/api/geolocation/8.8.8.8')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

def test_geolocation_invalid_ip(client):
    """Test geolocation with invalid IP."""
    response = client.get('/api/geolocation/invalid')
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'Invalid IP address'

def test_lookup_no_ip(client):
    """Test lookup without IP."""
    response = client.get('/api/lookup')
    assert response.status_code == 400

def test_bulk_lookup_too_many_ips(client):
    """Test bulk lookup with too many IPs."""
    response = client.post('/api/bulk_lookup', json={
        "ips": ["8.8.8.8"] * 51
    })
    assert response.status_code == 400
```

---

## 6. Docker поддержка

### docker/Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Run application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "wsgi:app"]
```

### docker/docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}
      - LOCAL_ONLY=True
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

---

## 7. CI/CD Pipeline

### .github/workflows/ci.yml
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements/dev.txt
    
    - name: Run linting
      run: |
        flake8 app tests
        black --check app tests
    
    - name: Run security scan
      run: |
        bandit -r app
        safety check
    
    - name: Run tests
      run: |
        pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

## 8. Миграция

### План миграции

1. **Фаза 1: Подготовка**
   - Создать новую структуру директорий
   - Настроить virtual environment
   - Установить зависимости

2. **Фаза 2: Перенос кода**
   - Создать application factory
   - Перенести routes в blueprints
   - Создать service layer
   - Добавить extensions

3. **Фаза 3: Тестирование**
   - Написать тесты
   - Проверить все endpoints
   - Проверить безопасность

4. **Фаза 4: Деплой**
   - Настроить Docker
   - Настроить CI/CD
   - Деплой в production

---

*Руководство создано: 2026-02-06*
