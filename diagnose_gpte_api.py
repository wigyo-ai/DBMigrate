"""
Detailed diagnostic script for H2O.ai GPTe API.
This will show detailed responses to help understand the API structure.
"""

import requests
import json

API_URL = "https://h2ogpte.internal.dedicated.h2o.ai/api"
API_KEY = "sk-3fQs4vrWxaHGDZslaZzaey71rH7sQj6trb8F7YiU9YxoOCkR"
MODEL_ID = "gpt-4.1-mini"

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

print("="*80)
print("H2O.ai GPTe API Detailed Diagnostics")
print("="*80)

# Test 1: Try to list available endpoints
print("\n1. Trying to get API info/health endpoint...")
try:
    for path in ['/', '/health', '/info', '/v1', '/api', '/docs']:
        url = f"{API_URL}{path}"
        print(f"\nGET {url}")
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        if response.text:
            print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Check what methods are accepted
print("\n" + "="*80)
print("2. Testing different HTTP methods on /v1/query...")
test_payload = {
    'question': 'Hello',
    'llm': MODEL_ID
}

for method in ['GET', 'POST', 'PUT']:
    try:
        url = f"{API_URL}/v1/query"
        print(f"\n{method} {url}")
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=test_payload, timeout=10)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=test_payload, timeout=10)

        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:1000]}")
    except Exception as e:
        print(f"Error: {e}")

# Test 3: Try different common H2O GPTe endpoints with detailed output
print("\n" + "="*80)
print("3. Testing common H2O.ai GPTe endpoint patterns...")

endpoints_to_test = [
    ('/v1/query', {'question': 'Say hello', 'llm': MODEL_ID}),
    ('/v1/query', {'prompt': 'Say hello', 'llm': MODEL_ID}),
    ('/v1/query', {'text': 'Say hello', 'model': MODEL_ID}),
    ('/query', {'question': 'Say hello', 'llm': MODEL_ID}),
    ('/v1/chat/completions', {
        'model': MODEL_ID,
        'messages': [{'role': 'user', 'content': 'Say hello'}]
    }),
    ('/v1/generate', {'prompt': 'Say hello', 'model': MODEL_ID}),
    ('/v1/ask', {'question': 'Say hello', 'llm': MODEL_ID}),
]

for endpoint, payload in endpoints_to_test:
    try:
        url = f"{API_URL}{endpoint}"
        print(f"\n{'='*80}")
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(url, headers=headers, json=payload, timeout=30)

        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")

        try:
            data = response.json()
            print(f"Response JSON:")
            print(json.dumps(data, indent=2)[:1000])
        except:
            print(f"Response Text: {response.text[:1000]}")

        if response.status_code == 200:
            print("\n" + "🎉"*40)
            print("SUCCESS! This endpoint works!")
            print("🎉"*40)
            break

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

# Test 4: Check if it's an OpenAI-compatible endpoint
print("\n" + "="*80)
print("4. Testing OpenAI-compatible format...")
try:
    url = f"{API_URL}/v1/chat/completions"
    payload = {
        'model': MODEL_ID,
        'messages': [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': 'Say hello'}
        ],
        'temperature': 0.7
    }
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:1000]}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*80)
print("Diagnosis complete!")
print("="*80)
