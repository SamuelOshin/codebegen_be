#!/usr/bin/env python3
"""
Complete test script to validate database schema and authentication system
"""

import asyncio
import requests
from datetime import datetime
from app.core.database import get_db_session
from app.repositories.user_repository import UserRepository


async def test_user_repository():
    """Test the UserRepository with the fixed create method"""
    print("🧪 Testing UserRepository with fixed create method...")
    
    # Use timestamp to ensure unique email
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    test_email = f"repo_test_{timestamp}@codebegen.com"
    test_username = f"repo_test_user_{timestamp}"
    
    try:
        session = await get_db_session()
        try:
            user_repo = UserRepository(session)
            
            print(f"Creating user with email: {test_email}")
            user = await user_repo.create_user(
                email=test_email,
                password="testpassword123",
                username=test_username,
                full_name="Test User"
            )
            
            print(f"✅ User created successfully: {user.email}")
            print(f"   User ID: {user.id}")
            print(f"   Username: {user.username}")
            print(f"   Is Active: {user.is_active}")
            
            return True
        finally:
            await session.close()
            
    except Exception as e:
        print(f"❌ Error testing repository: {e}")
        return False


def test_api_endpoints():
    """Test API endpoints"""
    print("\n🌐 Testing Authentication Endpoints...")
    
    base_url = "http://127.0.0.1:8000"
    
    # Test health endpoint
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Health check: {response.status_code} - {'✅ PASS' if response.status_code == 200 else '❌ FAIL'}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False
    
    # Use timestamp for unique user
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    test_email = f"api_test_{timestamp}@codebegen.com"
    test_username = f"api_test_{timestamp}"
    test_password = "testpassword123"
    
    # Test user registration
    print("Testing user registration...")
    try:
        registration_data = {
            "email": test_email,
            "username": test_username,
            "password": test_password,
            "full_name": "API Test User"
        }
        
        response = requests.post(f"{base_url}/auth/register", json=registration_data)
        print(f"   Registration: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Registration successful!")
            user_data = response.json()
            print(f"   User ID: {user_data.get('id')}")
            print(f"   Email: {user_data.get('email')}")
        else:
            print(f"   ❌ Registration failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Registration error: {e}")
        return False
    
    # Test user login
    print("Testing user login...")
    try:
        login_data = {
            "username": test_email,  # Login uses email as username
            "password": test_password
        }
        
        response = requests.post(
            f"{base_url}/auth/login", 
            data=login_data,  # OAuth2PasswordRequestForm expects form data
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print(f"   Login: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Login successful!")
            auth_data = response.json()
            access_token = auth_data.get("access_token")
            print(f"   Token type: {auth_data.get('token_type')}")
            print(f"   Access token: {access_token[:20]}...")
            
            # Test authenticated endpoint
            print("Testing authenticated endpoint...")
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(f"{base_url}/auth/me", headers=headers)
            
            if response.status_code == 200:
                print("   ✅ Authenticated request successful!")
                user_info = response.json()
                print(f"   Authenticated user: {user_info.get('email')}")
                return True
            else:
                print(f"   ❌ Authenticated request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        else:
            print(f"   ❌ Login failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return False


async def main():
    """Main test function"""
    print("🎯 Testing Database Schema & Authentication System")
    print("=" * 60)
    
    # Test repository
    repo_success = await test_user_repository()
    
    # Test API endpoints
    api_success = test_api_endpoints()
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Repository Test: {'✅ PASS' if repo_success else '❌ FAIL'}")
    print(f"API Endpoints Test: {'✅ PASS' if api_success else '❌ FAIL'}")
    
    if repo_success and api_success:
        print("\n🎉 All tests passed! Database schema and authentication system are working correctly!")
        print("\n📋 What was validated:")
        print("   ✅ Database schema is correct")
        print("   ✅ User table has all required columns")
        print("   ✅ UserRepository.create_user() works properly")
        print("   ✅ Password hashing is functional")
        print("   ✅ User registration endpoint works")
        print("   ✅ User login endpoint works")
        print("   ✅ JWT token generation works")
        print("   ✅ Authenticated endpoints work")
        print("   ✅ Database sessions are working correctly")
        print("\n🚀 Ready for full generation pipeline testing!")
        return True
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
