#!/usr/bin/env python
"""Test the admin login and password change endpoints."""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_admin_login():
    """Test admin login endpoint."""
    print("\n" + "="*60)
    print("TEST: Admin Login")
    print("="*60)
    
    # Test login with correct credentials
    payload = {
        "email": "aibuntysystems@gmail.com",
        "password": "Admin@2026!"
    }
    
    print(f"\nSending login request with email: {payload['email']}")
    
    try:
        response = requests.post(f"{BASE_URL}/api/admin/auth/login", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Login successful!")
            if data.get("token"):
                print(f"Session Token: {data['token'][:20]}... (truncated)")
                return data["token"], data.get("user", {})
            else:
                print("⚠️  No token returned")
        else:
            print(f"❌ Login failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    return None, None


def test_admin_change_password(token, user):
    """Test admin change password endpoint."""
    print("\n" + "="*60)
    print("TEST: Admin Change Password")
    print("="*60)
    
    payload = {
        "email": "aibuntysystems@gmail.com",
        "current_password": "Admin@2026!",
        "new_password": "Admin@2026!NewPass",
        "confirm_password": "Admin@2026!NewPass"
    }
    
    print(f"\nSending change password request for email: {payload['email']}")
    
    try:
        response = requests.post(f"{BASE_URL}/api/admin/auth/change-password", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
        
        if response.status_code == 200:
            print("\n✅ Password changed successfully!")
        else:
            print(f"❌ Password change failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def test_login_with_new_password():
    """Test login with the new password."""
    print("\n" + "="*60)
    print("TEST: Login with New Password")
    print("="*60)
    
    payload = {
        "email": "aibuntysystems@gmail.com",
        "password": "Admin@2026!NewPass"
    }
    
    print(f"\nAttempting to login with new password...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/admin/auth/login", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Login with new password successful!")
            if data.get("user", {}).get("passwordChanged"):
                print("✅ passwordChanged flag is TRUE (as expected)")
            else:
                print("⚠️  passwordChanged flag is FALSE (unexpected)")
        else:
            print(f"❌ Login with new password failed")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    print("\n\n" + "="*60)
    print("AdminAuth Testing Suite")
    print("="*60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Base URL: {BASE_URL}")
    
    # Test 1: Login
    token, user = test_admin_login()
    
    # Test 2: Change Password (only if login succeeded)
    if token:
        print(f"\n📝 Current passwordChanged value: {user.get('passwordChanged')}")
        test_admin_change_password(token, user)
    
        # Test 3: Login with new password
        test_login_with_new_password()
    
    print("\n" + "="*60)
    print("Testing Complete")
    print("="*60 + "\n")
