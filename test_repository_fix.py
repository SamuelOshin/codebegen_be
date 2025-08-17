#!/usr/bin/env python3
"""
Test script to validate the UserRepository fix and authentication system.
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from app.core.database import get_db_session
from app.repositories.user_repository import UserRepository
from app.core.security import get_password_hash, verify_password

async def test_user_repository():
    """Test the fixed UserRepository.create_user method"""
    print("🧪 Testing UserRepository with fixed create method...")
    
    # Get database session using the async context manager
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        
        try:
            # Try to create a user
            email = "repo_test2@codebegen.com"  # Use different email to avoid conflicts
            password = "test123456"
            print(f"Creating user with email: {email}")
            user = await user_repo.create_user(
                email=email,
                password=password,
                username="repo_test_user2"
            )
            print(f"✅ User created successfully!")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Username: {user.username}")
            print(f"   Has hashed password: {bool(user.hashed_password)}")
            print(f"   Is active: {user.is_active}")
            print(f"   Is superuser: {user.is_superuser}")
            
            # Test password verification
            print("\n🔐 Testing password verification...")
            password_valid = verify_password(password, user.hashed_password)
            print(f"   Password verification: {'✅ PASS' if password_valid else '❌ FAIL'}")
            
            # Test getting user by email
            print("\n🔍 Testing user lookup...")
            found_user = await user_repo.get_by_email(email)
            print(f"   User found by email: {'✅ PASS' if found_user else '❌ FAIL'}")
            
            if found_user:
                print(f"   Found user ID: {found_user.id}")
                print(f"   Found user email: {found_user.email}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing repository: {e}")
            print(f"   Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False

async def test_authentication_endpoints():
    """Test the authentication endpoints via HTTP"""
    print("\n🌐 Testing Authentication Endpoints...")
    
    import httpx
    
    base_url = "http://127.0.0.1:8000"
    
    try:
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            print("Testing health endpoint...")
            health_response = await client.get(f"{base_url}/health")
            print(f"   Health check: {health_response.status_code} - {'✅ PASS' if health_response.status_code == 200 else '❌ FAIL'}")
            
            # Test user registration
            print("\nTesting user registration...")
            register_data = {
                "email": "api_test2@codebegen.com",  # Use different email
                "password": "test123456"  # 8+ characters required
            }
            
            register_response = await client.post(
                f"{base_url}/auth/register",
                json=register_data
            )
            
            print(f"   Registration: {register_response.status_code}")
            if register_response.status_code == 200:  # Expecting 200, not 201
                print("   ✅ User registration successful!")
                user_data = register_response.json()
                print(f"   Created user: {user_data.get('email')}")
            else:
                print(f"   ❌ Registration failed: {register_response.text}")
                return False
            
            # Test user login
            print("\nTesting user login...")
            login_data = {
                "username": "api_test2@codebegen.com",  # OAuth2 expects 'username' field
                "password": "test123456"  # Use same password as registration
            }
            
            login_response = await client.post(
                f"{base_url}/auth/login",
                data=login_data,  # Form data, not JSON
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            print(f"   Login: {login_response.status_code}")
            if login_response.status_code == 200:
                print("   ✅ User login successful!")
                token_data = login_response.json()
                access_token = token_data.get("access_token")
                print(f"   Access token received: {access_token[:20]}...")
                
                # Test authenticated endpoint
                print("\nTesting authenticated endpoint...")
                headers = {"Authorization": f"Bearer {access_token}"}
                me_response = await client.get(f"{base_url}/auth/me", headers=headers)
                
                print(f"   Get current user: {me_response.status_code}")
                if me_response.status_code == 200:
                    print("   ✅ Authenticated endpoint access successful!")
                    user_info = me_response.json()
                    print(f"   Current user: {user_info.get('email')}")
                    return True
                else:
                    print(f"   ❌ Authenticated endpoint failed: {me_response.text}")
                    return False
                    
            else:
                print(f"   ❌ Login failed: {login_response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🎯 Testing Database Schema & Authentication System\n")
    print("=" * 60)
    
    # Test 1: Repository functionality
    repo_success = await test_user_repository()
    
    # Test 2: API endpoints
    api_success = await test_authentication_endpoints()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Repository Test: {'✅ PASS' if repo_success else '❌ FAIL'}")
    print(f"API Endpoints Test: {'✅ PASS' if api_success else '❌ FAIL'}")
    
    if repo_success and api_success:
        print("\n🎉 All tests passed! Database schema and authentication are working correctly!")
        print("✅ Ready for full generation pipeline testing!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return repo_success and api_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
