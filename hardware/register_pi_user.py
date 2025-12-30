"""
Register Pi User in Backend

Run this script ONCE to create the Raspberry Pi user account in the backend.
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Backend URL
API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api")

# Pi user credentials (from .env)
PI_USER = {
    "name": "Raspberry Pi",
    "email": os.getenv("PI_USER_EMAIL", "pi@sensegrid.local"),
    "password": os.getenv("PI_USER_PASSWORD", "sensegrid123")
}

print("=" * 60)
print("SenseGrid - Register Raspberry Pi User")
print("=" * 60)
print()
print(f"Backend: {API_URL}")
print(f"Email: {PI_USER['email']}")
print()

try:
    response = requests.post(
        f"{API_URL}/auth/register",
        json=PI_USER,
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Pi user registered successfully!")
        print()
        print(f"Name: {result['user']['name']}")
        print(f"Email: {result['user']['email']}")
        print(f"Token: {result['token'][:50]}...")
        print()
        print("🎉 You can now run pi_main.py")
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if "already registered" in response.text.lower():
            print()
            print("💡 User already exists! You can proceed with pi_main.py")
            
except Exception as e:
    print(f"❌ Connection error: {e}")
    print()
    print("⚠️  Make sure the backend is running:")
    print("   cd backend")
    print("   python -m uvicorn main:app --reload")

print()
print("=" * 60)
