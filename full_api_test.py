import requests
import json

print('🔄 Testing CodebeGen API Endpoints with Database...')

BASE_URL = 'http://127.0.0.1:8000'

# Test 1: Health check
print('\n1. Testing Health Endpoint...')
try:
    response = requests.get(f'{BASE_URL}/health')
    print(f'✅ Health Check: {response.status_code} - {response.json()}')
except Exception as e:
    print(f'❌ Health Check Failed: {e}')

# Test 2: User Registration
print('\n2. Testing User Registration...')
try:
    user_data = {
        'username': 'testuser2024',
        'email': 'test@example.com',
        'password': 'testpassword123',
        'full_name': 'Test User'
    }
    response = requests.post(f'{BASE_URL}/auth/register', json=user_data)
    print(f'Registration Response: {response.status_code}')
    
    if response.status_code == 201:
        print('✅ User registration successful')
        user_info = response.json()
        print(f'User ID: {user_info.get("id")}')
    elif response.status_code == 400:
        print('ℹ️ User might already exist - continuing with login')
    else:
        print(f'❌ Registration failed: {response.text}')
except Exception as e:
    print(f'❌ Registration Failed: {e}')

print('\n3. Testing User Login...')
try:
    login_data = {
        'username': 'testuser2024',
        'password': 'testpassword123'
    }
    response = requests.post(f'{BASE_URL}/auth/login', data=login_data)
    print(f'Login Response: {response.status_code}')
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data['access_token']
        print('✅ Login successful')
        
        # Headers for authenticated requests
        headers = {'Authorization': f'Bearer {access_token}'}
        
        print('\n4. Testing A/B Testing Endpoints...')
        response = requests.get(f'{BASE_URL}/api/v1/ab-testing/status', headers=headers)
        print(f'A/B Status: {response.status_code}')
        if response.status_code == 200:
            ab_data = response.json()
            print(f'✅ A/B Testing - Assignments: {ab_data.get("total_assignments", 0)}, Generations: {ab_data.get("total_generations", 0)}')
        
        print('\n5. Testing User Assignment...')
        response = requests.get(f'{BASE_URL}/api/v1/ab-testing/assignment/testuser2024', headers=headers)
        if response.status_code == 200:
            assignment = response.json()
            print(f'✅ User assigned to group: {assignment.get("group")}')
            print(f'Features enabled: {assignment.get("features_enabled")}')
        
        print('\n6. Testing Code Generation...')
        generation_request = {
            'prompt': 'Create a simple FastAPI endpoint for user management with CRUD operations',
            'context': {
                'domain': 'web_api',
                'complexity': 'medium'
            },
            'tech_stack': ['fastapi', 'sqlalchemy']
        }
        
        response = requests.post(f'{BASE_URL}/ai/generate', 
                               json=generation_request, 
                               headers=headers)
        print(f'Generation Response: {response.status_code}')
        
        if response.status_code == 200:
            generation_data = response.json()
            print(f'✅ Generation initiated')
            print(f'Generation ID: {generation_data.get("generation_id")}')
            print(f'Status: {generation_data.get("status")}')
            
            # Test generation status
            generation_id = generation_data.get('generation_id')
            if generation_id:
                print('\n7. Testing Generation Status...')
                status_response = requests.get(f'{BASE_URL}/generations/{generation_id}', headers=headers)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f'✅ Generation Status: {status_data.get("status")}')
                
        else:
            print(f'❌ Generation failed: {response.text}')
            
    else:
        print(f'❌ Login failed: {response.text}')
        
except Exception as e:
    print(f'❌ Login/Testing Failed: {e}')

print('\n🎉 API Testing Complete!')
