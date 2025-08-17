#!/usr/bin/env python3
"""
Test database authentication after fixing repository issue
"""

import asyncio
import requests
import json
from app.core.database import get_db_session
from app.repositories.user_repository import UserRepository
from app.models.user import User


async def create_test_user():
    """Create a test user if it doesn't exist"""
    print("🔧 Creating test user...")
    
    db = await get_db_session()
    try:
        user_repo = UserRepository(db)
        
        # Check if user already exists
        existing_user = await user_repo.get_by_email("test@codebegen.com")
        if existing_user:
            print("✅ Test user already exists!")
            return existing_user
        
        # Create new test user
        try:
            user = await user_repo.create_user(
                email="test@codebegen.com",
                password="test123",
                username="testuser",
                full_name="Test User",
                is_superuser=False
            )
            print(f"✅ Created test user: {user.email}")
            return user
        except Exception as e:
            print(f"❌ Failed to create user: {e}")
            return None
    finally:
        await db.close()


def test_authentication():
    """Test authentication endpoints"""
    print("\n🔐 Testing authentication endpoints...")
    
    base_url = "http://127.0.0.1:8000"
    
    # Test registration (should work now)
    print("\n1. Testing registration...")
    register_data = {
        "email": "newuser@codebegen.com",
        "password": "newpass123",
        "username": "newuser",
        "full_name": "New User"
    }
    
    try:
        response = requests.post(f"{base_url}/auth/register", json=register_data)
        print(f"Registration status: {response.status_code}")
        if response.status_code == 201:
            print("✅ Registration successful!")
            print(f"Response: {response.json()}")
        else:
            print(f"⚠️ Registration response: {response.text}")
    except Exception as e:
        print(f"❌ Registration error: {e}")
    
    # Test login with existing user
    print("\n2. Testing login...")
    login_data = {
        "username": "test@codebegen.com",  # OAuth2 uses username field for email
        "password": "test123"
    }
    
    try:
        response = requests.post(
            f"{base_url}/auth/login",
            data=login_data,  # Use form data, not JSON
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print(f"Login status: {response.status_code}")
        if response.status_code == 200:
            token_data = response.json()
            print("✅ Login successful!")
            print(f"Access token: {token_data.get('access_token', 'N/A')[:50]}...")
            return token_data.get('access_token')
        else:
            print(f"⚠️ Login response: {response.text}")
    except Exception as e:
        print(f"❌ Login error: {e}")
    
    return None


def test_protected_endpoints(access_token):
    """Test protected endpoints with authentication"""
    print("\n🔒 Testing protected endpoints...")
    
    base_url = "http://127.0.0.1:8000"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Test user profile
    print("\n1. Testing user profile...")
    try:
        response = requests.get(f"{base_url}/auth/me", headers=headers)
        print(f"Profile status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Profile access successful!")
            profile = response.json()
            print(f"User: {profile.get('email', 'N/A')}")
        else:
            print(f"⚠️ Profile response: {response.text}")
    except Exception as e:
        print(f"❌ Profile error: {e}")
    
    # Test A/B testing status
    print("\n2. Testing A/B testing status...")
    try:
        response = requests.get(f"{base_url}/api/v1/ab-testing/status", headers=headers)
        print(f"A/B testing status: {response.status_code}")
        if response.status_code == 200:
            print("✅ A/B testing access successful!")
            ab_data = response.json()
            print(f"Group: {ab_data.get('group', 'N/A')}")
            print(f"Features: {ab_data.get('features', {})}")
        else:
            print(f"⚠️ A/B testing response: {response.text}")
    except Exception as e:
        print(f"❌ A/B testing error: {e}")
    
    # Test generation endpoint
    print("\n3. Testing generation endpoint...")
    generation_data = {
        "prompt": "Create a simple FastAPI endpoint for user management",
        "project_type": "fastapi_basic",
        "requirements": ["CRUD operations", "authentication", "validation"]
    }
    
    try:
        response = requests.post(
            f"{base_url}/ai/generate",
            json=generation_data,
            headers=headers
        )
        print(f"Generation status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Generation request successful!")
            result = response.json()
            print(f"Generation ID: {result.get('id', 'N/A')}")
            print(f"Status: {result.get('status', 'N/A')}")
        else:
            print(f"⚠️ Generation response: {response.text}")
    except Exception as e:
        print(f"❌ Generation error: {e}")


async def main():
    """Main test function"""
    print("🎯 Database Authentication Test")
    print("=" * 40)
    
    # Create test user
    await create_test_user()
    
    # Test authentication
    access_token = test_authentication()
    
    # Test protected endpoints if we got a token
    if access_token:
        test_protected_endpoints(access_token)
    else:
        print("❌ Could not get access token, skipping protected endpoint tests")
    
    print("\n🎉 Authentication test complete!")


if __name__ == "__main__":
    asyncio.run(main())
