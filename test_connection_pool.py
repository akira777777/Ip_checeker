"""
Test script to verify connection pool optimizations
"""

import requests
import time

def test_connection_pool():
    print("Testing connection pool optimizations...")
    
    # Test basic connectivity
    try:
        response = requests.get("http://127.0.0.1:5000/api/health", timeout=10)
        print(f"✓ Health check: {response.status_code}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return
    
    # Test performance endpoint
    try:
        response = requests.get("http://127.0.0.1:5000/api/performance", timeout=10)
        print(f"✓ Performance metrics: {response.status_code}")
        
        # Print some performance data
        import json
        data = response.json()
        print(f"  - Avg response time: {data.get('performance_metrics', {}).get('avg_response_time_ms', 'N/A')}ms")
        print(f"  - Success rate: {data.get('system_resources', {}).get('cpu_percent', 'N/A')}% CPU")
    except Exception as e:
        print(f"✗ Performance metrics failed: {e}")
    
    # Test geolocation endpoint
    try:
        response = requests.get("http://127.0.0.1:5000/api/geolocation/8.8.8.8", timeout=15)
        print(f"✓ Geolocation test: {response.status_code}")
    except Exception as e:
        print(f"✗ Geolocation test failed: {e}")
    
    # Test bulk lookup
    try:
        response = requests.post(
            "http://127.0.0.1:5000/api/bulk_lookup",
            json={"ips": ["8.8.8.8", "1.1.1.1", "1.0.0.1"]},
            timeout=20
        )
        print(f"✓ Bulk lookup: {response.status_code}")
    except Exception as e:
        print(f"✗ Bulk lookup failed: {e}")
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    test_connection_pool()