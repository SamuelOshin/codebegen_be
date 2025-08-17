import requests

print('🔄 Testing Endpoints...')
BASE_URL = 'http://127.0.0.1:8000'

print('\n1. Testing A/B Testing Status...')
response = requests.get(f'{BASE_URL}/api/v1/ab-testing/status')
print(f'A/B Status: {response.status_code}')
if response.status_code == 200:
    data = response.json()
    print(f'✅ Assignments: {data.get("total_assignments", 0)}, Generations: {data.get("total_generations", 0)}')
elif response.status_code == 401:
    print('ℹ️ Requires authentication')

print('\n2. Testing A/B Testing Health...')
response = requests.get(f'{BASE_URL}/api/v1/ab-testing/health')
print(f'A/B Health: {response.status_code}')
if response.status_code == 200:
    health_data = response.json()
    print(f'✅ A/B Testing Health: {health_data.get("status")}')

print('\n3. Testing Generation Models Status...')
try:
    # Test if we can access AI generation endpoint without auth to see error
    response = requests.post(f'{BASE_URL}/ai/generate', json={'prompt': 'test'})
    print(f'Generation endpoint: {response.status_code}')
    if response.status_code == 401:
        print('✅ Generation requires authentication (expected)')
    elif response.status_code == 422:
        print('✅ Generation endpoint accessible (validation error expected)')
    else:
        print(f'Generation response: {response.text}')
except Exception as e:
    print(f'❌ Generation test failed: {e}')

print('\n✅ Basic endpoint testing complete')
