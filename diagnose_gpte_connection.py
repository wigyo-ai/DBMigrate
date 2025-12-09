"""
Comprehensive H2O.ai GPTe Connection Diagnostic Tool
Tests various aspects of the connection to identify issues.
"""
import sys
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("=" * 60)
print("H2O.ai GPTe Connection Diagnostic Tool")
print("=" * 60)
print()

# Get credentials from command line or prompt
if len(sys.argv) >= 3:
    api_url = sys.argv[1]
    api_key = sys.argv[2]
else:
    print("Usage: python diagnose_gpte_connection.py <api_url> <api_key>")
    print()
    api_url = input("Enter GPTe API URL: ").strip()
    api_key = input("Enter GPTe API Key: ").strip()

print(f"Testing connection to: {api_url}")
print(f"Using API key: {api_key[:10]}..." if len(api_key) > 10 else f"API key length: {len(api_key)}")
print()

# Test 1: Basic connectivity
print("Test 1: Network Connectivity")
print("-" * 40)
try:
    import requests
    response = requests.get(api_url, verify=False, timeout=10)
    print(f"✓ Can reach {api_url}")
    print(f"  Status: {response.status_code}")
    print(f"  Response size: {len(response.content)} bytes")
except requests.exceptions.Timeout:
    print(f"✗ Connection timeout - server unreachable")
    sys.exit(1)
except requests.exceptions.ConnectionError as e:
    print(f"✗ Connection failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    sys.exit(1)
print()

# Test 2: SDK Import
print("Test 2: H2OGPTE SDK Import")
print("-" * 40)
try:
    from h2ogpte import H2OGPTE
    print("✓ h2ogpte SDK imported successfully")
    import h2ogpte
    print(f"  SDK version: {h2ogpte.__version__ if hasattr(h2ogpte, '__version__') else 'unknown'}")
except ImportError as e:
    print(f"✗ Failed to import h2ogpte: {e}")
    sys.exit(1)
print()

# Test 3: SDK Initialization
print("Test 3: H2OGPTE Client Initialization")
print("-" * 40)
try:
    client = H2OGPTE(
        address=api_url,
        api_key=api_key,
        verify=False
    )
    print("✓ Client initialized successfully")
    print(f"  Client type: {type(client)}")
except TypeError as e:
    if "Meta()" in str(e):
        print("✗ Authentication failed - SDK received unexpected response")
        print(f"  Error: {e}")
        print()
        print("This typically means:")
        print("  1. API key is invalid or expired")
        print("  2. API key doesn't have permission to access this instance")
        print("  3. The API endpoint format has changed")
        sys.exit(1)
    else:
        print(f"✗ Type error: {e}")
        sys.exit(1)
except Exception as e:
    print(f"✗ Initialization failed: {e}")
    print(f"  Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# Test 4: Get available models
print("Test 4: Query Available Models")
print("-" * 40)
try:
    models = client.get_llms()
    print("✓ Successfully retrieved model list")
    print(f"  Available models: {len(models)}")
    for model in models[:5]:  # Show first 5
        print(f"    - {model}")
    if len(models) > 5:
        print(f"    ... and {len(models) - 5} more")
except Exception as e:
    print(f"✗ Failed to get models: {e}")
    print("  (This might be a permission issue)")
print()

# Test 5: Simple question
print("Test 5: Send Test Question")
print("-" * 40)
try:
    response = client.answer_question(
        question="Hello, can you respond with just the word 'SUCCESS'?",
        llm="gpt-4.1-mini",
        timeout=30
    )
    print("✓ Successfully sent test question")
    print(f"  Response type: {type(response)}")
    if hasattr(response, 'content'):
        print(f"  Response content: {response.content[:100]}...")
    else:
        print(f"  Response: {str(response)[:100]}...")
except Exception as e:
    print(f"✗ Failed to send question: {e}")
    print(f"  Error type: {type(e).__name__}")
print()

print("=" * 60)
print("Diagnostic Complete!")
print("=" * 60)
print()
print("If all tests passed, your configuration is correct.")
print("If any tests failed, review the error messages above.")
