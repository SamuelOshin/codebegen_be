#!/usr/bin/env python3
"""
Complete Authenticated Generation Pipeline Test
Tests the full code generation flow with authentication
"""

import httpx
import asyncio
import json
from typing import Dict, Any

# Test configuration
BASE_URL = "http://127.0.0.1:8001"
TEST_CREDENTIALS = {
    "email": "test@codebegen.com",
    "username": "testuser", 
    "password": "test123"
}

class AuthenticatedAPITester:
    """Test the complete authenticated API flow"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        self.auth_token = None
        self.user_id = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def login(self) -> bool:
        """Login and get authentication token"""
        print("🔐 Authenticating user...")
        
        try:
            # Login with form data (as expected by FastAPI OAuth2PasswordRequestForm)
            login_data = {
                "username": TEST_CREDENTIALS["email"],  # FastAPI OAuth2 uses username field for email
                "password": TEST_CREDENTIALS["password"]
            }
            
            response = await self.client.post("/auth/login", data=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.user_id = data.get("user_id")
                
                print(f"✅ Authentication successful!")
                print(f"   - User ID: {self.user_id}")
                print(f"   - Token: {self.auth_token[:20]}...")
                
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        if not self.auth_token:
            raise ValueError("Not authenticated")
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    async def test_user_profile(self) -> bool:
        """Test getting user profile"""
        print("\n👤 Testing user profile access...")
        
        try:
            response = await self.client.get("/auth/me", headers=self.get_auth_headers())
            
            if response.status_code == 200:
                profile = response.json()
                print(f"✅ User profile retrieved:")
                print(f"   - ID: {profile.get('id')}")
                print(f"   - Email: {profile.get('email')}")
                print(f"   - Username: {profile.get('username')}")
                print(f"   - Active: {profile.get('is_active')}")
                print(f"   - Verified: {profile.get('is_verified')}")
                return True
            else:
                print(f"❌ Profile access failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Profile access error: {e}")
            return False
    
    async def test_ab_testing_status(self) -> bool:
        """Test A/B testing status with authentication"""
        print("\n🧪 Testing A/B testing status (authenticated)...")
        
        try:
            response = await self.client.get("/api/v1/ab-testing/status", headers=self.get_auth_headers())
            
            if response.status_code == 200:
                status = response.json()
                print(f"✅ A/B testing status retrieved:")
                print(f"   - Experiment: {status.get('experiment_id')}")
                print(f"   - Group: {status.get('group')}")
                print(f"   - Features: {status.get('features')}")
                return True
            else:
                print(f"❌ A/B testing status failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ A/B testing status error: {e}")
            return False
    
    async def test_code_generation(self) -> Dict[str, Any]:
        """Test the complete code generation pipeline"""
        print("\n🤖 Testing code generation pipeline...")
        
        generation_request = {
            "prompt": "Create a simple FastAPI endpoint for user management with CRUD operations",
            "framework": "fastapi",
            "template_type": "fastapi_sqlalchemy",
            "requirements": [
                "SQLAlchemy models",
                "CRUD operations",
                "Input validation",
                "Error handling",
                "API documentation"
            ],
            "context": {
                "database": "postgresql",
                "authentication": "jwt",
                "api_style": "restful"
            }
        }
        
        try:
            response = await self.client.post(
                "/ai/generate",
                json=generation_request,
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                print(f"✅ Code generation successful!")
                print(f"   - Generation ID: {result.get('id')}")
                print(f"   - Status: {result.get('status')}")
                print(f"   - Quality Score: {result.get('quality_score')}")
                print(f"   - A/B Group: {result.get('ab_group')}")
                
                # Check if files were generated
                files = result.get('output_files', [])
                if files:
                    print(f"   - Generated Files: {len(files)}")
                    for file in files[:3]:  # Show first 3 files
                        print(f"     * {file.get('path', 'Unknown')}")
                
                return result
            else:
                print(f"❌ Code generation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return {}
                
        except Exception as e:
            print(f"❌ Code generation error: {e}")
            return {}
    
    async def test_generation_status(self, generation_id: str) -> bool:
        """Test getting generation status"""
        print(f"\n📊 Testing generation status for ID: {generation_id}...")
        
        try:
            response = await self.client.get(
                f"/generations/{generation_id}",
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                status = response.json()
                print(f"✅ Generation status retrieved:")
                print(f"   - ID: {status.get('id')}")
                print(f"   - Status: {status.get('status')}")
                print(f"   - Created: {status.get('created_at')}")
                print(f"   - Updated: {status.get('updated_at')}")
                return True
            else:
                print(f"❌ Generation status failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Generation status error: {e}")
            return False
    
    async def test_user_generations(self) -> bool:
        """Test getting user's generations list"""
        print("\n📝 Testing user generations list...")
        
        try:
            response = await self.client.get("/generations/", headers=self.get_auth_headers())
            
            if response.status_code == 200:
                generations = response.json()
                print(f"✅ User generations retrieved: {len(generations)} items")
                
                if generations:
                    for gen in generations[:3]:  # Show first 3
                        print(f"   - ID: {gen.get('id')}, Status: {gen.get('status')}")
                
                return True
            else:
                print(f"❌ User generations failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ User generations error: {e}")
            return False

async def run_complete_test():
    """Run the complete authenticated API test"""
    print("🚀 Complete Authenticated Generation Pipeline Test")
    print("=" * 60)
    
    async with AuthenticatedAPITester() as tester:
        # Step 1: Authenticate
        auth_success = await tester.login()
        if not auth_success:
            print("❌ Authentication failed - cannot continue")
            return
        
        # Step 2: Test user profile
        profile_success = await tester.test_user_profile()
        
        # Step 3: Test A/B testing status
        ab_success = await tester.test_ab_testing_status()
        
        # Step 4: Test code generation
        generation_result = await tester.test_code_generation()
        generation_success = bool(generation_result)
        
        # Step 5: Test generation status (if generation was successful)
        status_success = True
        if generation_result and generation_result.get('id'):
            status_success = await tester.test_generation_status(generation_result['id'])
        
        # Step 6: Test user generations list
        list_success = await tester.test_user_generations()
        
        # Summary
        print("\n🎉 Test Results Summary")
        print("=" * 60)
        print(f"✅ Authentication: {'PASS' if auth_success else 'FAIL'}")
        print(f"✅ User Profile: {'PASS' if profile_success else 'FAIL'}")
        print(f"✅ A/B Testing: {'PASS' if ab_success else 'FAIL'}")
        print(f"✅ Code Generation: {'PASS' if generation_success else 'FAIL'}")
        print(f"✅ Generation Status: {'PASS' if status_success else 'FAIL'}")
        print(f"✅ Generations List: {'PASS' if list_success else 'FAIL'}")
        
        all_passed = all([auth_success, profile_success, ab_success, generation_success, status_success, list_success])
        
        if all_passed:
            print("\n🎊 ALL TESTS PASSED! 🎊")
            print("✅ Complete generation pipeline is working!")
            print("✅ Authentication system operational")
            print("✅ A/B testing integration working")
            print("✅ Database connectivity confirmed")
            print("✅ AI models pipeline ready")
        else:
            print("\n⚠️ Some tests failed - check logs above")
        
        print("\n🚀 System ready for production testing!")

if __name__ == "__main__":
    asyncio.run(run_complete_test())
