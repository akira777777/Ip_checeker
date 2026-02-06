"""Integration tests for IP Checker API"""
import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def run_tests():
    print("Additional Integration Tests")
    print("=" * 60)

    # Test map generation endpoint
    print("\n[1] Map Generation Endpoint:")
    try:
        resp = requests.post(f"{BASE_URL}/api/map", json={"ips": ["8.8.8.8", "1.1.1.1"]}, timeout=15)
        print(f"    Status: {resp.status_code}")
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "")
            print(f"    Content-Type: {content_type}")
            if "json" in content_type:
                data = resp.json()
                print(f"    Locations found: {len(data.get('locations', []))}")
            else:
                print(f"    HTML map generated: {len(resp.text)} bytes")
        else:
            print(f"    Response: {resp.text[:100]}")
    except Exception as e:
        print(f"    Error: {e}")

    # Test health check details
    print("\n[2] Health Check Details:")
    try:
        resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
        data = resp.json()
        print(f"    Status: {data.get('status')}")
        print(f"    Version: {data.get('version')}")
        print(f"    Platform: {data.get('platform', 'unknown')[:30]}...")
        print(f"    Cache Entries: {data.get('geo_cache_entries', 0)}")
        print(f"    IPAPI Available: {data.get('ipapi_available', False)}")
        print(f"    WHOIS Available: {data.get('whois_available', False)}")
    except Exception as e:
        print(f"    Error: {e}")

    # Test myip details
    print("\n[3] My IP Details:")
    try:
        resp = requests.get(f"{BASE_URL}/api/myip", timeout=5)
        data = resp.json()
        print(f"    IP: {data.get('ip', 'unknown')}")
        print(f"    Timestamp: {data.get('timestamp', 'unknown')}")
    except Exception as e:
        print(f"    Error: {e}")

    # Test geolocation response structure
    print("\n[4] Geolocation Response Structure:")
    try:
        resp = requests.get(f"{BASE_URL}/api/geolocation/8.8.8.8", timeout=10)
        data = resp.json()
        fields = ["ip", "city", "country", "country_code", "lat", "lon", "timezone", "isp", "status"]
        for field in fields:
            value = data.get(field, "MISSING")
            if field in ["lat", "lon"]:
                print(f"    {field}: {value}")
            else:
                print(f"    {field}: {str(value)[:30]}")
    except Exception as e:
        print(f"    Error: {e}")

    # Test lookup response structure
    print("\n[5] Lookup Response Structure:")
    try:
        resp = requests.get(f"{BASE_URL}/api/lookup?ip=8.8.8.8", timeout=10)
        data = resp.json()
        print(f"    success: {data.get('success')}")
        print(f"    ip: {data.get('ip')}")
        print(f"    geolocation: {type(data.get('geolocation')).__name__}")
        print(f"    whois: {type(data.get('whois')).__name__}")
        print(f"    reverse_dns: {type(data.get('reverse_dns')).__name__}")
    except Exception as e:
        print(f"    Error: {e}")

    # Test security scan structure
    print("\n[6] Security Scan Structure:")
    try:
        resp = requests.get(f"{BASE_URL}/api/security/scan", timeout=10)
        data = resp.json()
        print(f"    score: {data.get('score')}")
        print(f"    timestamp: {data.get('timestamp', 'unknown')}")
        print(f"    findings count: {len(data.get('findings', []))}")
        print(f"    recommendations count: {len(data.get('recommendations', []))}")
    except Exception as e:
        print(f"    Error: {e}")

    # Test investigate structure
    print("\n[7] Investigate Response Structure:")
    try:
        resp = requests.get(f"{BASE_URL}/api/investigate", timeout=10)
        data = resp.json()
        print(f"    hostname: {data.get('hostname', 'unknown')}")
        print(f"    platform: {str(data.get('platform', 'unknown'))[:30]}...")
        print(f"    interfaces count: {len(data.get('interfaces', []))}")
        print(f"    connections count: {len(data.get('connections', []))}")
        summary = data.get("summary", {})
        print(f"    total_connections: {summary.get('total_connections', 0)}")
        security = data.get("security", {})
        print(f"    security score: {security.get('score', 0)}")
    except Exception as e:
        print(f"    Error: {e}")

    print("\n" + "=" * 60)
    print("Integration tests completed!")


if __name__ == "__main__":
    run_tests()
