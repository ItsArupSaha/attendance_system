"""
Quick setup checker - verifies Firebase configuration and connection.
Run this to diagnose setup issues before running full tests.
"""
import os
import sys
from dotenv import load_dotenv

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def check_env_file():
    """Check if .env file exists."""
    print(f"{BLUE}{BOLD}Checking .env file...{RESET}")
    if os.path.exists('.env'):
        print(f"{GREEN}✓ .env file exists{RESET}")
        return True
    else:
        print(f"{RED}✗ .env file not found{RESET}")
        print(f"{YELLOW}  Create it by copying .env.example{RESET}")
        return False

def check_env_variables():
    """Check if required environment variables are set."""
    print(f"\n{BLUE}{BOLD}Checking environment variables...{RESET}")
    load_dotenv()
    
    required_vars = [
        'FIREBASE_PROJECT_ID',
        'FIREBASE_PRIVATE_KEY',
        'FIREBASE_CLIENT_EMAIL',
    ]
    
    optional_vars = [
        'FIREBASE_TYPE',
        'FIREBASE_PRIVATE_KEY_ID',
        'FIREBASE_CLIENT_ID',
        'COOLDOWN_MINUTES',
        'FLASK_HOST',
        'FLASK_PORT',
    ]
    
    all_ok = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'EMAIL' in var:
                display = value[:20] + '...' if len(value) > 20 else value
            else:
                display = value
            print(f"{GREEN}✓ {var} = {display}{RESET}")
        else:
            print(f"{RED}✗ {var} is missing{RESET}")
            all_ok = False
    
    print(f"\n{YELLOW}Optional variables:{RESET}")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"{GREEN}✓ {var} = {value}{RESET}")
        else:
            print(f"{YELLOW}○ {var} (using default){RESET}")
    
    return all_ok

def check_firebase_connection():
    """Check if Firebase connection works."""
    print(f"\n{BLUE}{BOLD}Checking Firebase connection...{RESET}")
    try:
        import database
        db = database.get_db()
        print(f"{GREEN}✓ Firestore connection successful{RESET}")
        return True
    except ValueError as e:
        print(f"{RED}✗ Configuration error: {e}{RESET}")
        return False
    except Exception as e:
        print(f"{RED}✗ Connection error: {e}{RESET}")
        print(f"{YELLOW}  Make sure Firestore is enabled in Firebase Console{RESET}")
        return False

def main():
    """Run all checks."""
    print(f"{BOLD}{BLUE}{'='*60}")
    print("Backend Setup Checker")
    print(f"{'='*60}{RESET}\n")
    
    checks = [
        ("Environment File", check_env_file),
        ("Environment Variables", check_env_variables),
        ("Firebase Connection", check_firebase_connection),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"{RED}Error in {name}: {e}{RESET}")
            results.append((name, False))
    
    # Summary
    print(f"\n{BOLD}{BLUE}{'='*60}")
    print("Summary")
    print(f"{'='*60}{RESET}\n")
    
    all_passed = all(result for _, result in results)
    
    for name, result in results:
        status = f"{GREEN}✓ PASS{RESET}" if result else f"{RED}✗ FAIL{RESET}"
        print(f"{status} - {name}")
    
    if all_passed:
        print(f"\n{GREEN}{BOLD}All checks passed! Backend is ready to use.{RESET}\n")
        return 0
    else:
        print(f"\n{YELLOW}{BOLD}Some checks failed. Please fix the issues above.{RESET}\n")
        return 1

if __name__ == '__main__':
    # Fix Windows encoding
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    exit_code = main()
    sys.exit(exit_code)
