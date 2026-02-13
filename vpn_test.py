import requests
import json

print("=== IP Checker VPN Compatibility Test ===\n")

# Test 1: Health check
print("1. Health Check:")
health = requests.get('http://127.0.0.1:5000/api/health').json()
print(f"   Status: {health['status']}")
print(f"   Version: {health['version']}")
print(f"   Cache entries: {health['cache_entries']}")
print(f"   Local only mode: {health['local_only']}")

# Test 2: My IP detection
print("\n2. My IP Detection:")
myip = requests.get('http://127.0.0.1:5000/api/myip').json()
print(f"   Detected IP: {myip['ip']}")
print(f"   Timestamp: {myip['timestamp']}")

# Test 3: External IP geolocation
print("\n3. External IP Geolocation (8.8.8.8):")
geo = requests.get('http://127.0.0.1:5000/api/geolocation/8.8.8.8').json()
if geo['status'] == 'success':
    print(f"   Location: {geo['city']}, {geo['country']}")
    print(f"   ISP: {geo['isp']}")
    print(f"   Coordinates: {geo['lat']}, {geo['lon']}")
else:
    print(f"   Error: {geo.get('message', 'Unknown error')}")

# Test 4: Network investigation
print("\n4. Network Investigation:")
investigate = requests.get('http://127.0.0.1:5000/api/investigate').json()
print(f"   Total connections: {investigate['summary']['total_connections']}")
print(f"   Security score: {investigate['security']['score']}/100")
print(f"   Grade: {investigate['security']['grade']}")

print("\n   Sample external connections:")
for i, conn in enumerate(investigate['connections'][:3]):
    if conn.get('geo', {}).get('status') == 'success':
        country = conn['geo'].get('country', 'Unknown')
        print(f"   {i+1}. {conn['remote_addr']} -> {country}")

# Test 5: Security scan
print("\n5. Security Scan:")
security = requests.get('http://127.0.0.1:5000/api/security/scan').json()
print(f"   Threats detected: {security['summary']['threats']}")
print(f"   Warnings: {security['summary']['warnings']}")
print(f"   Recommendations: {len(security['recommendations'])}")

print("\n=== Test Complete ===")