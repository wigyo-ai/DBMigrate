"""
Test H2OGPTE client initialization to diagnose the error.
"""
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from h2ogpte import H2OGPTE

# Test configuration
API_URL = "https://h2ogpte.internal.dedicated.h2o.ai"
API_KEY = "sk-test-key"  # Replace with actual key

print("Testing H2OGPTE initialization...")
print(f"API URL: {API_URL}")
print(f"API Key: {API_KEY[:10]}...")
print()

try:
    print("Attempting to initialize H2OGPTE client...")
    client = H2OGPTE(
        address=API_URL,
        api_key=API_KEY,
        verify=False
    )
    print("✓ Client initialized successfully!")
    print(f"Client type: {type(client)}")
    print(f"Client attributes: {dir(client)}")

    # Try to get available models
    print("\nAttempting to get available models...")
    try:
        models = client.get_llms()
        print(f"✓ Available models: {models}")
    except Exception as e:
        print(f"✗ Failed to get models: {e}")
        print(f"Error type: {type(e)}")

except Exception as e:
    print(f"✗ Failed to initialize client!")
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")

    # Try to get more details
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()
