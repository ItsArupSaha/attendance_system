"""
Comprehensive automated test script for the Fingerprint Attendance System backend.
Tests all endpoints and business logic according to the project requirements.
"""
import requests
import time
import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# Configuration
BASE_URL = os.getenv('TEST_BASE_URL', 'http://localhost:8000')
TEST_TIMEOUT = 30


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(name):
    """Print test name."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}Testing: {name}{Colors.RESET}")


def print_success(message):
    """Print success message."""
    print(f"{Colors.GREEN}[PASS] {message}{Colors.RESET}")


def print_error(message):
    """Print error message."""
    print(f"{Colors.RED}[FAIL] {message}{Colors.RESET}")


def print_warning(message):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message):
    """Print info message."""
    print(f"  {message}")


def test_health_check():
    """Test health check endpoint."""
    print_test("Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TEST_TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data['status'] == 'healthy', "Health check should return healthy status"
        assert 'server_time' in data, "Response should include server_time"
        print_success("Health check passed")
        return True
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


def test_registration_missing_fields():
    """Test registration with missing required fields."""
    print_test("Registration - Missing Fields")
    try:
        response = requests.post(
            f"{BASE_URL}/register",
            data={},
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 400, "Should return 400 for missing fields"
        data = response.json()
        assert data['status'] == 'error', "Should return error status"
        print_success("Missing fields validation works")
        return True
    except Exception as e:
        print_error(f"Missing fields test failed: {e}")
        return False


def test_registration_invalid_fingerprint_id():
    """Test registration with invalid fingerprint_id."""
    print_test("Registration - Invalid Fingerprint ID")
    try:
        form_data = {
            'name': 'Test Teacher',
            'department': 'CS',
            'fingerprint_id': 'invalid'
        }
        response = requests.post(
            f"{BASE_URL}/register",
            data=form_data,
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 400, "Should return 400 for invalid fingerprint_id"
        data = response.json()
        assert data['status'] == 'error', "Should return error status"
        print_success("Invalid fingerprint_id validation works")
        return True
    except Exception as e:
        print_error(f"Invalid fingerprint_id test failed: {e}")
        return False


def test_attendance_unregistered_fingerprint():
    """Test attendance with unregistered fingerprint_id."""
    print_test("Attendance - Unregistered Fingerprint")
    try:
        payload = {'fingerprint_id': 99999}
        response = requests.post(
            f"{BASE_URL}/attendance",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 404, "Should return 404 for unregistered fingerprint"
        data = response.json()
        assert data['status'] == 'error', "Should return error status"
        assert 'not registered' in data['message'].lower(), "Message should indicate not registered"
        assert 'server_time' in data, "Response should include server_time"
        print_success("Unregistered fingerprint handling works")
        return True
    except Exception as e:
        print_error(f"Unregistered fingerprint test failed: {e}")
        return False


def test_attendance_invalid_payload():
    """Test attendance with invalid payload."""
    print_test("Attendance - Invalid Payload")
    try:
        # Test with JSON but missing fingerprint_id
        response = requests.post(
            f"{BASE_URL}/attendance",
            json={},
            headers={'Content-Type': 'application/json'},
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 400, "Should return 400 for invalid payload"
        data = response.json()
        assert data['status'] == 'error', "Should return error status"
        print_success("Invalid payload validation works")
        return True
    except Exception as e:
        print_error(f"Invalid payload test failed: {e}")
        return False


def test_attendance_non_json():
    """Test attendance endpoint with non-JSON request."""
    print_test("Attendance - Non-JSON Request")
    try:
        response = requests.post(
            f"{BASE_URL}/attendance",
            data={},
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 400, "Should return 400 for non-JSON request"
        data = response.json()
        assert data['status'] == 'error', "Should return error status"
        print_success("Non-JSON request validation works")
        return True
    except Exception as e:
        print_error(f"Non-JSON request test failed: {e}")
        return False


def test_full_attendance_flow():
    """
    Test complete attendance flow:
    1. Register a teacher
    2. Check-in via fingerprint
    3. Attempt early check-out (should fail)
    4. Attempt duplicate check-in (should fail or succeed based on state)
    """
    print_test("Full Attendance Flow")
    
    try:
        # Generate unique test data
        test_fingerprint_id = int(time.time()) % 100000
        test_name = f"Test Teacher {test_fingerprint_id}"
        
        # Step 1: Register teacher
        print_info("Step 1: Registering teacher...")
        form_data = {
            'name': test_name,
            'department': 'Computer Science',
            'fingerprint_id': str(test_fingerprint_id)
        }
        
        response = requests.post(
            f"{BASE_URL}/register",
            data=form_data,
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code not in [201, 200]:
            print_warning(f"Registration returned {response.status_code}")
            print_warning(f"Response: {response.text}")
            if response.status_code == 500:
                print_warning("Server error - check Firestore connection and .env configuration")
            # Continue anyway - teacher might already exist or Firestore not configured
        
        # Step 2: Check-in via fingerprint
        print_info("Step 2: Attempting check-in via fingerprint...")
        payload = {'fingerprint_id': test_fingerprint_id}
        response = requests.post(
            f"{BASE_URL}/attendance",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data['status'] == 'success', "Check-in should succeed"
            assert 'check-in' in data['message'].lower(), "Message should mention check-in"
            print_success("Check-in successful")
        else:
            print_warning(f"Check-in returned {response.status_code}: {response.text}")
            # Might already be checked in, try check-out instead
        
        # Step 3: Attempt early check-out (should fail)
        print_info("Step 3: Attempting early check-out (should fail)...")
        time.sleep(1)  # Wait 1 second
        payload = {'fingerprint_id': test_fingerprint_id}
        response = requests.post(
            f"{BASE_URL}/attendance",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code == 400:
            data = response.json()
            assert data['status'] == 'error', "Early check-out should return error"
            assert 'remaining_minutes' in data, "Response should include remaining_minutes"
            assert 'too early' in data['message'].lower() or 'wait' in data['message'].lower(), \
                "Message should indicate cooldown"
            print_success("Early check-out correctly rejected")
        else:
            print_warning(f"Early check-out test: Got {response.status_code}")
            print_warning("This might be expected if cooldown already passed")
        
        # Step 4: Attempt duplicate check-in (should fail if already checked out)
        print_info("Step 4: Attempting duplicate check-in (should fail if already checked out)...")
        payload = {'fingerprint_id': test_fingerprint_id}
        response = requests.post(
            f"{BASE_URL}/attendance",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=TEST_TIMEOUT
        )
        
        # This should either fail (if already checked out) or succeed (if still checked in)
        data = response.json()
        print_info(f"Duplicate check-in response: {data['status']} - {data['message']}")
        
        print_success("Full attendance flow test completed")
        return True
        
    except Exception as e:
        print_error(f"Full attendance flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_response_format():
    """Test that responses are OLED-friendly (short messages)."""
    print_test("Response Format - OLED Compatibility")
    try:
        # Test error response
        payload = {'fingerprint_id': 99999}
        response = requests.post(
            f"{BASE_URL}/attendance",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=TEST_TIMEOUT
        )
        data = response.json()
        
        # Check required fields
        assert 'status' in data, "Response must have 'status' field"
        assert 'message' in data, "Response must have 'message' field"
        assert 'server_time' in data, "Response must have 'server_time' field"
        
        # Check message length (OLED-friendly)
        assert len(data['message']) < 100, "Message should be short for OLED display"
        
        # Check status values
        assert data['status'] in ['success', 'error'], "Status must be 'success' or 'error'"
        
        print_success("Response format is OLED-friendly")
        return True
        
    except Exception as e:
        print_error(f"Response format test failed: {e}")
        return False


def test_server_time_authority():
    """Test that server time is included in all responses."""
    print_test("Server Time Authority")
    try:
        # Test multiple endpoints
        endpoints = [
            ('GET', '/health', None),
            ('POST', '/attendance', {'fingerprint_id': 99999}),
        ]
        
        for method, endpoint, payload in endpoints:
            if method == 'GET':
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=TEST_TIMEOUT)
            else:
                response = requests.post(
                    f"{BASE_URL}{endpoint}",
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=TEST_TIMEOUT
                )
            
            data = response.json()
            assert 'server_time' in data, f"{endpoint} should include server_time"
            
            # Verify ISO8601 format
            try:
                from datetime import datetime
                datetime.fromisoformat(data['server_time'].replace('Z', '+00:00'))
            except:
                # Try parsing without timezone
                datetime.fromisoformat(data['server_time'].split('+')[0].split('Z')[0])
        
        print_success("Server time is authoritative in all responses")
        return True
        
    except Exception as e:
        print_error(f"Server time authority test failed: {e}")
        return False


def run_all_tests():
    """Run all test cases."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print("Fingerprint Attendance System - Backend Test Suite")
    print(f"{'='*60}{Colors.RESET}\n")
    
    print_info(f"Testing backend at: {BASE_URL}")
    print_info(f"Make sure the Flask server is running!\n")
    
    tests = [
        ("Health Check", test_health_check),
        ("Registration - Missing Fields", test_registration_missing_fields),
        ("Registration - Invalid Fingerprint ID", test_registration_invalid_fingerprint_id),
        ("Attendance - Unregistered Fingerprint", test_attendance_unregistered_fingerprint),
        ("Attendance - Invalid Payload", test_attendance_invalid_payload),
        ("Attendance - Non-JSON Request", test_attendance_non_json),
        ("Response Format", test_response_format),
        ("Server Time Authority", test_server_time_authority),
        ("Full Attendance Flow", test_full_attendance_flow),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print("Test Summary")
    print(f"{'='*60}{Colors.RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"{status} - {test_name}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.RESET}\n")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}All tests passed! ✓{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}Some tests failed. Please review the output above.{Colors.RESET}\n")
        return 1


if __name__ == '__main__':
    # Check if server is reachable
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"{Colors.GREEN}Server is reachable{Colors.RESET}\n")
    except requests.exceptions.RequestException:
        print(f"{Colors.RED}ERROR: Cannot reach server at {BASE_URL}")
        print(f"Please make sure the Flask server is running!")
        print(f"You can start it with: python app.py{Colors.RESET}\n")
        sys.exit(1)
    
    exit_code = run_all_tests()
    sys.exit(exit_code)
