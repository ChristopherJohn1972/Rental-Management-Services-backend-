import sys
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("=== TESTING CURRENT ENDPOINTS ===")

# Test 1: /api/auth/me
print("\n1. Testing /api/auth/me...")
try:
    response = client.get("/api/auth/me")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:100]}...")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: /api/properties  
print("\n2. Testing /api/properties...")
try:
    response = client.get("/api/properties")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:100]}...")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: /health (should work)
print("\n3. Testing /health...")
try:
    response = client.get("/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")
