#!/usr/bin/env python3
"""
Quick start script for BoxCostPython development.
Run this script to verify your setup and start the development server.
"""
import subprocess
import sys
import os
from pathlib import Path


def check_python_version():
    """Check if Python version is 3.11 or higher."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print(f"❌ Python 3.11+ required. You have {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_virtual_env():
    """Check if running in a virtual environment."""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    if in_venv:
        print("✅ Virtual environment activated")
    else:
        print("⚠️  Not in a virtual environment. Run: venv\\Scripts\\activate")
    return in_venv


def check_env_file():
    """Check if .env file exists."""
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
        return True
    else:
        print("⚠️  .env file not found. Copy .env.example to .env and configure")
        return False


def check_dependencies():
    """Check if required packages are installed."""
    try:
        import fastapi
        import sqlalchemy
        import pydantic
        print("✅ Core dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies. Run: pip install -r requirements.txt")
        print(f"   Error: {e}")
        return False


def run_health_check():
    """Run a quick health check on the API."""
    print("\n🔍 Running health check...")
    try:
        import httpx
        response = httpx.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is running and healthy")
            return True
        else:
            print("⚠️  API returned unexpected status:", response.status_code)
            return False
    except Exception as e:
        print("ℹ️  API not running (this is OK if you haven't started it yet)")
        return False


def main():
    """Main function to run all checks."""
    print("=" * 60)
    print("BoxCostPython - Development Environment Check")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_env),
        ("Environment File", check_env_file),
        ("Dependencies", check_dependencies),
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("✅ All checks passed! Ready to start development.")
        print("\nTo start the development server, run:")
        print("  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
        print("\nAPI will be available at:")
        print("  - Root: http://localhost:8000")
        print("  - Docs: http://localhost:8000/docs")
        print("  - ReDoc: http://localhost:8000/redoc")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\nQuick setup steps:")
        print("  1. Activate virtual environment: venv\\Scripts\\activate")
        print("  2. Install dependencies: pip install -r requirements.txt")
        print("  3. Copy .env file: cp .env.example .env")
        print("  4. Configure .env with your database and API keys")
    
    print("=" * 60)
    
    # Try to run health check if API might be running
    run_health_check()


if __name__ == "__main__":
    main()
