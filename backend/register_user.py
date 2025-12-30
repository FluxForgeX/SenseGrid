"""
Quick user registration script for SenseGrid backend.
Run this ONCE to create your user account.
"""

import requests

# SenseGrid backend URL (NOT Roboflow)
API_URL = "http://localhost:8000/api"

# Your details (change these!)
USER_DATA = {
    "name": "Your Name",
    "email": "hmdebrahim6@gmail.com",
    "password": "YourPassword123"  # Choose any password
}

print("=" * 60)
print("SenseGrid User Registration")
print("=" * 60)
print()

# Register user
try:
    response = requests.post(
        f"{API_URL}/auth/register",
        json=USER_DATA,
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Registration successful!")
        print()
        print(f"Name: {result['user']['name']}")
        print(f"Email: {result['user']['email']}")
        print(f"Token: {result['token'][:50]}...")
        print()
        print("🎉 You can now use test_detection_api.py with these credentials:")
        print(f"   Email: {USER_DATA['email']}")
        print(f"   Password: {USER_DATA['password']}")
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if "already registered" in response.text.lower():
            print()
            print("💡 User already exists! Use these credentials to login:")
            print(f"   Email: {USER_DATA['email']}")
            print(f"   Password: {USER_DATA['password']}")
            
except Exception as e:
    print(f"❌ Error: {e}")
    print()
    print("⚠️ Make sure the backend is running:")
    print("   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000")

print()
print("=" * 60)
