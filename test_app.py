"""
Test suite for IP Checker Application
Tests all backend functions without requiring Flask server
"""
import json
import socket
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch, Mock

# Add project root to path
sys.path.insert(0, 'd:\\Ip_checeker')

# Create proper mocks BEFORE importing app
mock_ipapi = MagicMock()
mock_ipapi.location = MagicMock(return_value=None)

mock_whois = MagicMock()
mock_whois_lib = MagicMock()
mock_whois_lib.whois = MagicMock()

mock_folium = MagicMock()
mock_folium.Map = MagicMock(return_value=MagicMock())
mock_folium.Marker = MagicMock(return_value=MagicMock())
mock_folium.Popup = MagicMock(return_value=MagicMock())
mock_folium.Icon = MagicMock(return_value=MagicMock())
mock_folium.tile_layer = MagicMock()

mock_psutil = MagicMock()
mock_psutil.Process = MagicMock(side_effect=Exception("No such process"))
mock_psutil.net_if_addrs = MagicMock(return_value={})
mock_psutil.net_connections = MagicMock(return_value=[])
mock_psutil.NoSuchProcess = Exception
mock_psutil.AccessDenied = Exception
mock_psutil.ZombieProcess = Exception
mock_psutil.AF_INET = socket.AF_INET
mock_psutil.AF_INET6 = socket.AF_INET6

# Inject mocks
sys.modules['ipapi'] = mock_ipapi
sys.modules['whois'] = mock_whois
sys.modules['python_whois'] = mock_whois_lib
sys.modules['folium'] = mock_folium
sys.modules['psutil'] = mock_psutil

import app


class TestIPGeolocation(unittest.TestCase):
    """Test IP geolocation functionality"""
    
    def test_get_ip_geolocation_with_cache(self):
        """Test geolocation caching"""
        app.GEO_CACHE["1.2.3.4"] = (9999999999, {"ip": "1.2.3.4", "city": "Test"})
        result = app.get_ip_geolocation("1.2.3.4")
        self.assertEqual(result["city"], "Test")
        del app.GEO_CACHE["1.2.3.4"]
    
    @patch('app.requests.get')
    def test_get_ip_geolocation_api_success(self, mock_get):
        """Test successful API geolocation lookup"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "city": "Mountain View",
            "country": "United States",
            "countryCode": "US",
            "regionName": "California",
            "lat": 37.386,
            "lon": -122.0838,
            "timezone": "America/Los_Angeles",
            "isp": "Google LLC",
            "as": "AS15169 Google LLC"
        }
        mock_get.return_value = mock_response
        
        # Clear cache to ensure API call
        if "8.8.8.8" in app.GEO_CACHE:
            del app.GEO_CACHE["8.8.8.8"]
        
        result = app.get_ip_geolocation("8.8.8.8")
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["city"], "Mountain View")
        self.assertEqual(result["country"], "United States")
    
    @patch('app.requests.get')
    def test_get_ip_geolocation_api_fail(self, mock_get):
        """Test failed API geolocation lookup"""
        mock_get.side_effect = Exception("Connection error")
        
        # Clear cache
        if "invalid" in app.GEO_CACHE:
            del app.GEO_CACHE["invalid"]
        
        result = app.get_ip_geolocation("invalid")
        
        self.assertEqual(result["status"], "error")
        self.assertIn("message", result)


class TestReverseDNS(unittest.TestCase):
    """Test reverse DNS lookup functionality"""
    
    @patch('app.socket.gethostbyaddr')
    def test_reverse_dns_success(self, mock_gethostbyaddr):
        """Test successful reverse DNS lookup"""
        mock_gethostbyaddr.return_value = ("dns.google", [], ["8.8.8.8"])
        
        result = app.reverse_dns_lookup("8.8.8.8")
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["hostname"], "dns.google")
    
    @patch('app.socket.gethostbyaddr')
    def test_reverse_dns_failure(self, mock_gethostbyaddr):
        """Test failed reverse DNS lookup"""
        mock_gethostbyaddr.side_effect = socket.herror("Not found")
        
        result = app.reverse_dns_lookup("invalid.ip")
        
        self.assertEqual(result["status"], "error")


class TestWhois(unittest.TestCase):
    """Test WHOIS functionality"""
    
    def test_whois_unavailable(self):
        """Test WHOIS when library not available"""
        # Save original
        original_whois = app.whois_lib
        app.whois_lib = None
        
        result = app.get_whois_info("8.8.8.8")
        self.assertEqual(result["status"], "unavailable")
        
        # Restore
        app.whois_lib = original_whois


class TestConnectionClassification(unittest.TestCase):
    """Test connection classification and security"""
    
    def test_classify_suspicious_port(self):
        """Test detection of suspicious ports"""
        level, risks = app.classify_connection(4444, "ESTABLISHED", {})
        self.assertEqual(level, "danger")
        self.assertTrue(any("commonly abused" in r for r in risks))
    
    def test_classify_secure_port(self):
        """Test secure port classification"""
        level, risks = app.classify_connection(443, "ESTABLISHED", {"status": "success"})
        self.assertEqual(level, "info")
        self.assertEqual(len(risks), 0)
    
    def test_classify_non_standard_state(self):
        """Test non-standard connection state"""
        level, risks = app.classify_connection(8080, "SYN_SENT", {"status": "success"})
        self.assertEqual(level, "warning")
    
    def test_aggregate_security(self):
        """Test security aggregation"""
        connections = [
            {"risk_level": "info", "remote_port": 443},
            {"risk_level": "warning", "remote_port": 8080},
            {"risk_level": "danger", "remote_port": 4444},
        ]
        result = app.aggregate_security(connections)
        
        self.assertEqual(result["warnings"], 1)  # warning + danger levels (both non-info)
        self.assertEqual(result["threats"], 1)
        self.assertEqual(result["secure"], 1)
        self.assertLessEqual(result["score"], 100)
        self.assertGreaterEqual(result["score"], 30)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    def test_safe_process_name_none(self):
        """Test safe process name with None PID"""
        self.assertEqual(app.safe_process_name(None), "unknown")


class TestAppRoutes(unittest.TestCase):
    """Test Flask routes"""
    
    def setUp(self):
        """Set up test client"""
        app.app.testing = True
        self.client = app.app.test_client()
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["version"], app.APP_VERSION)
    
    def test_myip_endpoint(self):
        """Test myip endpoint"""
        with patch('app.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ip": "1.2.3.4"}
            mock_get.return_value = mock_response
            
            response = self.client.get('/api/myip')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn("ip", data)
            self.assertIn("timestamp", data)
    
    def test_lookup_endpoint_no_ip(self):
        """Test lookup endpoint without IP"""
        response = self.client.get('/api/lookup')
        self.assertEqual(response.status_code, 400)
    
    def test_report_endpoint(self):
        """Test report endpoint"""
        response = self.client.get('/api/report')
        self.assertEqual(response.status_code, 200)
    
    def test_report_html_format(self):
        """Test report endpoint with HTML format"""
        response = self.client.get('/api/report?format=html')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<html>', response.data)
    
    def test_security_scan_endpoint(self):
        """Test security scan endpoint"""
        response = self.client.get('/api/security/scan')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("score", data)
        self.assertIn("recommendations", data)
    
    def test_investigate_endpoint(self):
        """Test investigate endpoint"""
        response = self.client.get('/api/investigate')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("hostname", data)
        self.assertIn("platform", data)
    
    def test_scan_alias_endpoint(self):
        """Test scan endpoint (alias for investigate)"""
        response = self.client.get('/api/scan')
        self.assertEqual(response.status_code, 200)
    
    def test_index_page(self):
        """Test main page loads"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'IP Checker Pro', response.data)


def run_tests():
    """Run all tests and generate report"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestIPGeolocation))
    suite.addTests(loader.loadTestsFromTestCase(TestReverseDNS))
    suite.addTests(loader.loadTestsFromTestCase(TestWhois))
    suite.addTests(loader.loadTestsFromTestCase(TestConnectionClassification))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilityFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestAppRoutes))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("="*60)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
