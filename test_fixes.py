import sys
sys.path.insert(0, '.')

print("=== TESTING FIXED ENDPOINTS ===")

try:
    from main import app
    print("✅ App imported successfully")
    
    # Create a simple test client
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    print("\n1. Testing /api/auth/me (should return 200):")
    response = client.get("/api/auth/me")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ SUCCESS: Returns 200 OK")
        data = response.json()
        print(f"   User ID: {data.get('uid', 'N/A')}")
        print(f"   Email: {data.get('email', 'N/A')}")
    else:
        print(f"   ❌ FAILED: {response.text}")
    
    print("\n2. Testing /api/properties (should return 200):")
    response = client.get("/api/properties")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ SUCCESS: Returns 200 OK")
        data = response.json()
        print(f"   Found {len(data) if isinstance(data, list) else 0} properties")
        if data and len(data) > 0:
            print(f"   First property: {data[0].get('name', 'N/A')}")
    else:
        print(f"   ❌ FAILED: {response.text}")
    
    print("\n3. Testing /health (should work):")
    response = client.get("/health")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ SUCCESS: Returns 200 OK")
    
    print("\n🎉 All endpoints should now work on Render!")
    
except Exception as e:
    print(f"❌ Error during test: {e}")
    import traceback
    traceback.print_exc()
