#!/usr/bin/env python3
"""
Quick generation status checker
"""
import requests
import json

def check_generation_status():
    # Login
    auth_data = {"username": "admin", "password": "password"}
    auth_response = requests.post("http://127.0.0.1:8000/auth/login", data=auth_data)
    
    if auth_response.status_code != 200:
        print(f"❌ Auth failed: {auth_response.text}")
        return
    
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Check generation status
    generation_id = "cf0eab15-f6d5-46cf-81e5-add7763b9c43"
    
    response = requests.get(f"http://127.0.0.1:8000/generations/{generation_id}", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("🔍 Generation Status:")
        print(f"   Status: {data.get('status')}")
        print(f"   Quality Score: {data.get('quality_score')}")
        print(f"   Error: {data.get('error_message')}")
        print(f"   Updated: {data.get('updated_at')}")
        print(f"   Total Time: {data.get('total_time')}")
        
        # Check artifacts
        artifacts = data.get('artifacts', [])
        print(f"   Artifacts: {len(artifacts)} files")
        
        if data.get('status') == 'failed':
            print(f"❌ Generation failed: {data.get('error_message')}")
        elif data.get('status') == 'completed':
            print("✅ Generation completed!")
            for artifact in artifacts[:3]:  # Show first 3 artifacts
                print(f"   📄 {artifact.get('file_path')}")
                
    else:
        print(f"❌ Status check failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    check_generation_status()
