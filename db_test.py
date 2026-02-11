import requests
import json
import os

print("=== IP Checker Database Integration Test ===\n")

# Test 1: Enhanced health check
print("1. Enhanced Health Check:")
health = requests.get('http://127.0.0.1:5000/api/health').json()
print(f"   Status: {health['status']}")
print(f"   Version: {health['version']}")
print(f"   Database available: {health.get('database', {}).get('available', 'Unknown')}")
print(f"   Database status: {health.get('database', {}).get('status', 'Unknown')}")

# Test 2: Database initialization (if configured)
print("\n2. Database Initialization:")
try:
    init_response = requests.get('http://127.0.0.1:5000/api/db/init')
    if init_response.status_code == 200:
        print("   Database tables created successfully")
    else:
        print(f"   Database init failed: {init_response.json()}")
except Exception as e:
    print(f"   Database init error: {e}")

# Test 3: Geolocation lookup (should use hybrid caching)
print("\n3. Geolocation Lookup Test:")
geo_response = requests.get('http://127.0.0.1:5000/api/geolocation/8.8.8.8')
geo_data = geo_response.json()
print(f"   IP: {geo_data.get('ip')}")
print(f"   Location: {geo_data.get('city')}, {geo_data.get('country')}")
print(f"   Cached: {geo_data.get('cached', False)}")
print(f"   Status: {geo_data.get('status')}")

# Test 4: Bulk lookup to test caching
print("\n4. Bulk Lookup Test:")
bulk_data = {"ips": ["8.8.8.8", "1.1.1.1", "9.9.9.9"]}
bulk_response = requests.post('http://127.0.0.1:5000/api/bulk_lookup', json=bulk_data)
if bulk_response.status_code == 200:
    bulk_results = bulk_response.json()
    print(f"   Processed {len(bulk_results.get('results', []))} IPs")
    for result in bulk_results.get('results', [])[:2]:
        geo = result.get('geolocation', {})
        print(f"   - {result['ip']}: {geo.get('city', 'Unknown')}, {geo.get('country', 'Unknown')}")

print("\n=== Database Integration Test Complete ===")
print("\nTo configure database:")
print("1. Set DATABASE_URL environment variable")
print("2. Run migrate_db.py to create tables")
print("3. Restart the application")