#!/usr/bin/env python3
"""
Debug 422 validation errors in generation endpoint
"""
import requests
import json
import time

# Test configuration
API_BASE_URL = "http://127.0.0.1:8000"

def test_auth_and_project():
    """Test authentication and project creation only"""
    print("🔐 Testing Authentication...")
    
    # Test authentication
    auth_data = {
        "username": "testuser2024",
        "password": "TestPassword123!"
    }
    
    response = requests.post(f"{API_BASE_URL}/auth/login", data=auth_data)
    print(f"Auth response: {response.status_code}")
    if response.status_code != 200:
        print(f"Auth failed: {response.text}")
        return None, None
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Authentication successful")
    
    # Test project creation
    print("📁 Testing Project Creation...")
    project_data = {
        "name": "Test E-commerce Backend",
        "description": "Test project for comprehensive pipeline validation",
        "domain": "ecommerce",
        "tech_stack": ["fastapi", "postgresql", "pydantic"],
        "constraints": {
            "max_file_size": 50,
            "include_tests": True,
            "include_documentation": True
        }
    }
    
    response = requests.post(f"{API_BASE_URL}/projects/", json=project_data, headers=headers)
    print(f"Project response: {response.status_code}")
    if response.status_code != 201:
        print(f"Project creation failed: {response.text}")
        return None, None
    
    project_id = response.json()["id"]
    print(f"✅ Project created: {project_id}")
    
    return headers, project_id

def test_generation_minimal():
    """Test generation with minimal data"""
    headers, project_id = test_auth_and_project()
    if not headers or not project_id:
        return
    
    print("🤖 Testing Minimal Generation Request...")
    
    # Minimal generation data
    generation_data = {
        "prompt": "Create a simple FastAPI hello world endpoint",
        "project_id": project_id
    }
    
    response = requests.post(f"{API_BASE_URL}/ai/generate", json=generation_data, headers=headers)
    print(f"Generation response: {response.status_code}")
    print(f"Response body: {response.text}")
    
    if response.status_code == 422:
        try:
            error_detail = response.json()
            print("📋 Validation errors:")
            for error in error_detail.get("detail", []):
                print(f"  • {error}")
        except:
            pass

def test_generation_full():
    """Test generation with full data"""
    headers, project_id = test_auth_and_project()
    if not headers or not project_id:
        return
    
    print("🤖 Testing Full Generation Request...")
    
    # Full generation data
    generation_data = {
        "prompt": "Create a FastAPI e-commerce backend with user authentication, product catalog, shopping cart, and order management. Include PostgreSQL database models, Pydantic schemas, CRUD operations, and API endpoints.",
        "project_id": project_id,
        "context": {
            "domain": "ecommerce",
            "tech_stack": "fastapi_postgresql",
            "features": ["authentication", "products", "cart", "orders"],
            "requirements": [
                "RESTful API design",
                "JWT authentication",
                "Database migrations",
                "Input validation",
                "Error handling"
            ]
        },
        "is_iteration": False,
        "parent_generation_id": None
    }
    
    response = requests.post(f"{API_BASE_URL}/ai/generate", json=generation_data, headers=headers)
    print(f"Generation response: {response.status_code}")
    print(f"Response body: {response.text}")
    
    if response.status_code == 422:
        try:
            error_detail = response.json()
            print("📋 Validation errors:")
            for error in error_detail.get("detail", []):
                print(f"  • {error}")
        except:
            pass

if __name__ == "__main__":
    print("🔍 Debugging Generation Endpoint 422 Errors")
    print("=" * 50)
    
    # Wait for server
    print("⏳ Waiting for server...")
    time.sleep(3)
    
    print("\n1. Testing minimal generation request:")
    test_generation_minimal()
    
    print("\n2. Testing full generation request:")
    test_generation_full()
