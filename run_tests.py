"""
Automated test runner that starts the server and runs all tests.
"""
import subprocess
import time
import sys
import os
import requests

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

BASE_URL = 'http://localhost:8000'

def check_server_running():
    """Check if server is already running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_server():
    """Start the Flask server in background."""
    print(f"{BLUE}{BOLD}Starting Flask server...{RESET}")
    
    # Check if server is already running
    if check_server_running():
        print(f"{GREEN}Server is already running!{RESET}\n")
        return None
    
    # Start server
    process = subprocess.Popen(
        [sys.executable, 'app.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    print(f"{YELLOW}Waiting for server to start...{RESET}")
    for i in range(10):
        time.sleep(1)
        if check_server_running():
            print(f"{GREEN}Server started successfully!{RESET}\n")
            return process
        print(f"  Attempt {i+1}/10...")
    
    print(f"{RED}Failed to start server!{RESET}")
    return None

def run_tests():
    """Run the test suite."""
    print(f"{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}Running Backend Tests{RESET}")
    print(f"{BLUE}{BOLD}{'='*60}{RESET}\n")
    
    result = subprocess.run([sys.executable, 'test_backend.py'], 
                          capture_output=False)
    return result.returncode

def main():
    """Main function."""
    # Start server
    server_process = start_server()
    
    if server_process is None and not check_server_running():
        print(f"{RED}Cannot proceed without server. Exiting.{RESET}")
        sys.exit(1)
    
    try:
        # Run tests
        exit_code = run_tests()
        
        return exit_code
    finally:
        # Clean up: kill server if we started it
        if server_process:
            print(f"\n{YELLOW}Stopping server...{RESET}")
            server_process.terminate()
            server_process.wait()
            print(f"{GREEN}Server stopped.{RESET}")

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
