import sys
sys.path.insert(0, '.')

print("=== SIMPLE ENDPOINT TEST ===")

# Just import the app to see if it loads
try:
    from main import app
    print("✅ App imported successfully")
    
    # List all endpoints
    print(f"\n📋 Endpoints found ({len(app.routes)}):")
    for route in app.routes:
        if hasattr(route, 'methods'):
            methods = list(route.methods)
            print(f"  {methods[0]} {route.path}")
            
except Exception as e:
    print(f"❌ Error importing app: {e}")
    import traceback
    traceback.print_exc()
