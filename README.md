# IP Checker Pro - Network Intelligence Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.0+](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive network intelligence platform for IP geolocation, network analysis, and security monitoring.

## ✨ Features

- 🔍 **IP Geolocation** - Detailed location data for any IP address
- 🛡️ **Security Scanning** - Analyze active connections and detect risks
- 🗺️ **Interactive Maps** - Visualize IP locations with clustering
- 📊 **Real-time Dashboard** - Live network activity monitoring
- 📈 **Analytics Charts** - Connection types and geographic distribution
- 🔎 **PC Investigation** - Deep system network analysis
- 📄 **Report Generation** - Export comprehensive reports

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ip_checker
```

2. Create virtual environment:
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables (optional):
```bash
cp .env.example .env
# Edit .env file with your settings
```

5. Run the application:
```bash
python app.py
```

6. Open in browser:
```
http://127.0.0.1:5000
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | Auto-generated | Flask secret key |
| `LOCAL_ONLY` | `true` | Restrict access to local network |
| `FLASK_DEBUG` | `false` | Enable debug mode |
| `FLASK_HOST` | `127.0.0.1` | Server host |
| `FLASK_PORT` | `5000` | Server port |
| `FORCE_HTTPS` | `false` | Force HTTPS in production |
| `GEO_CACHE_TTL` | `3600` | Geolocation cache TTL (seconds) |
| `GEO_LOOKUP_LIMIT` | `15` | Max geolocation lookups per scan |
| `MAX_BULK_LOOKUPS` | `100` | Max IPs in bulk lookup |
| `MAX_CONNECTIONS_SCAN` | `200` | Max connections to analyze |

### Security Settings

**Important**: For production deployment:

1. Set a strong `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
export SECRET_KEY="your-generated-key"
```

2. Disable debug mode:
```bash
export FLASK_DEBUG=false
```

3. Enable HTTPS:
```bash
export FORCE_HTTPS=true
```

4. Keep `LOCAL_ONLY=true` unless you have authentication

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Docker directly

```bash
# Build image
docker build -t ip-checker-pro .

# Run container
docker run -d \
  -p 5000:5000 \
  -e SECRET_KEY="your-secret-key" \
  -e LOCAL_ONLY=true \
  --name ip-checker \
  ip-checker-pro
```

## 📡 API Endpoints

### Health Check
```
GET /api/health
```

### IP Geolocation
```
GET /api/geolocation/<ip>
```

### Comprehensive Lookup
```
GET /api/lookup?ip=<ip>
POST /api/lookup
{
  "ip": "8.8.8.8"
}
```

### Bulk Lookup
```
POST /api/bulk_lookup
{
  "ips": ["8.8.8.8", "1.1.1.1"]
}
```

### Security Scan
```
GET /api/security/scan
```

### PC Investigation
```
GET /api/investigate
```

### Generate Report
```
GET /api/report?format=json&include_system=true
```

### Generate Map
```
POST /api/map
{
  "ips": ["8.8.8.8", "1.1.1.1"]
}
```

## 🔒 Security Considerations

### Local Access Only (Recommended)

By default, the application only accepts connections from:
- 127.0.0.0/8 (localhost)
- 10.0.0.0/8 (private)
- 172.16.0.0/12 (private)
- 192.168.0.0/16 (private)
- IPv6 loopback and link-local addresses

### Rate Limiting

Default limits:
- 200 requests per day
- 50 requests per hour
- 30 requests per minute for heavy endpoints

### Security Headers

The application includes:
- Content Security Policy (CSP)
- X-Content-Type-Options
- X-Frame-Options
- Strict-Transport-Security (when HTTPS enabled)

## 🧪 Testing

```bash
# Run tests
python test_app.py

# Run with coverage
pytest --cov=app tests/
```

## 🛠️ Development

### Code Quality

```bash
# Format code
black app.py

# Lint code
flake8 app.py

# Security scan
bandit -r app.py
```

### Project Structure

```
ip_checker/
├── app.py                 # Main application
├── requirements.txt       # Dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose setup
├── .env.example          # Example environment config
├── templates/
│   └── index.html        # Main UI template
├── static/
│   ├── style.css         # Stylesheets
│   ├── main.js           # Application logic
│   └── script.js         # UI shell
└── backups/              # Backup files
```

## 📝 Changelog

### Version 2.1.0 (Security Hardened)
- ✅ Added SECRET_KEY configuration
- ✅ Added IP validation using ipaddress module
- ✅ Added rate limiting with Flask-Limiter
- ✅ Added security headers with Flask-Talisman
- ✅ Fixed local access enforcement
- ✅ Added retry logic for API calls
- ✅ Fixed temp file cleanup for maps
- ✅ Fixed cache for negative geolocation results
- ✅ Improved exception handling

### Version 2.0.0
- Initial stable release
- IP geolocation functionality
- Network connection analysis
- Security scanning
- Interactive maps
- Report generation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and feature requests, please use the GitHub issue tracker.

## 🔗 Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flask-Security](https://flask-security-too.readthedocs.io/)
- [IP Geolocation API](https://ip-api.com/)

---

**Note**: This tool is for legitimate network analysis and security purposes only. Always comply with applicable laws and regulations.
