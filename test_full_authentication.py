#!/usr/bin/env python3
"""
Test the authentication endpoints with the test user
"""

import requests
import json

def test_authentication():
    """Test login and generation endpoints"""
    base_url = "http://127.0.0.1:8000"
    
    # Test user credentials
    credentials = {
        "username": "test@codebegen.com", 
        "password": "test123"
    }
    
    print("🔐 Testing Authentication System")
    print("=" * 50)
    
    try:
        # Test login
        print("\n1. Testing login endpoint...")
        login_response = requests.post(
            f"{base_url}/auth/login",
            data=credentials,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"   Status: {login_response.status_code}")
        print(f"   Response: {login_response.text[:200]}...")
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data.get("access_token")
            print(f"   ✅ Login successful! Token: {access_token[:50]}...")
            
            # Test protected endpoints with token
            headers = {"Authorization": f"Bearer {access_token}"}
            
            print("\n2. Testing protected endpoints...")
            
            # Test user profile
            profile_response = requests.get(f"{base_url}/auth/me", headers=headers)
            print(f"   /auth/me: {profile_response.status_code}")
            if profile_response.status_code == 200:
                print(f"   User: {profile_response.json().get('email')}")
            
            # Test A/B testing status
            ab_response = requests.get(f"{base_url}/api/v1/ab-testing/status", headers=headers)
            print(f"   /api/v1/ab-testing/status: {ab_response.status_code}")
            if ab_response.status_code == 200:
                ab_data = ab_response.json()
                print(f"   A/B Group: {ab_data.get('group')}")
                print(f"   Features: {ab_data.get('features')}")
            
            # Test generation endpoint
            print("\n3. Testing code generation endpoint...")
            generation_request = {
                "prompt": "Create a simple FastAPI endpoint for user management with CRUD operations",
                "project_type": "fastapi_basic",
                "additional_context": "Include proper error handling and validation"
            }
            
            gen_response = requests.post(
                f"{base_url}/ai/generate",
                json=generation_request,
                headers=headers
            )
            
            print(f"   Status: {gen_response.status_code}")
            print(f"   Response: {gen_response.text[:300]}...")
            
            if gen_response.status_code == 200:
                gen_data = gen_response.json()
                print(f"   ✅ Generation successful!")
                print(f"   Generation ID: {gen_data.get('generation_id')}")
                print(f"   Status: {gen_data.get('status')}")
                if 'files' in gen_data:
                    print(f"   Files generated: {len(gen_data['files'])}")
                    for file_info in gen_data['files'][:2]:  # Show first 2 files
                        print(f"      - {file_info.get('name')} ({file_info.get('type')})")
            
            return True
        else:
            print(f"   ❌ Login failed: {login_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing authentication: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_authentication()
    if success:
        print("\n🎉 Authentication system fully validated!")
    else:
        print("\n❌ Authentication test failed!")
        exit(1)
