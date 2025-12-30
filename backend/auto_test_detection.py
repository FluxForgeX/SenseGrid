import requests
import sys
from pathlib import Path

API_URL = "http://localhost:8000/api"
EMAIL = "al@mail.com"
PASSWORD = "123456"
IMAGE_PATH = "cow.jpg"

def main():
    if not Path(IMAGE_PATH).exists():
        print(f"Error: {IMAGE_PATH} not found")
        return

    # 1. Login
    print(f"Logging in as {EMAIL}...")
    try:
        resp = requests.post(f"{API_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            return
        token = resp.json()["token"]
        print("Login successful.")
    except Exception as e:
        print(f"Connection error: {e}")
        return

    # 2. Detect
    print(f"Sending {IMAGE_PATH} for detection...")
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": open(IMAGE_PATH, "rb")}
    
    try:
        resp = requests.post(f"{API_URL}/intruder/detect", headers=headers, files=files)
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Detection error: {e}")

if __name__ == "__main__":
    main()
