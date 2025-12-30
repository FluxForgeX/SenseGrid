"""
Simple test script for intruder detection API endpoint.

Usage:
    python test_detection_api.py path/to/image.jpg

Requirements:
    - Backend must be running on http://localhost:8000
    - You must have a registered user account
"""

import sys
import requests
from pathlib import Path


def main():
    # Configuration
    API_URL = "http://localhost:8000/api"
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python test_detection_api.py <image_path>")
        print("Example: python test_detection_api.py test-image.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    # Validate image file
    if not Path(image_path).exists():
        print(f"❌ Error: Image file not found: {image_path}")
        sys.exit(1)
    
    # Get credentials
    print("=" * 60)
    print("SenseGrid Intruder Detection API Test")
    print("=" * 60)
    print()
    
    email = input("Enter your email: ")
    password = input("Enter your password: ")
    print()
    
    # Step 1: Login
    print("🔐 Logging in...")
    try:
        login_response = requests.post(
            f"{API_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        login_response.raise_for_status()
        token = login_response.json()["token"]
        print(f"✅ Login successful")
        print()
    except requests.exceptions.RequestException as e:
        print(f"❌ Login failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)
    
    # Step 2: Upload image for detection
    print(f"📤 Uploading image: {image_path}")
    print("🔍 Running intruder detection...")
    print()
    
    try:
        with open(image_path, "rb") as f:
            detection_response = requests.post(
                f"{API_URL}/intruder/detect",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("image.jpg", f, "image/jpeg")},
                timeout=30
            )
        
        detection_response.raise_for_status()
        result = detection_response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Detection failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)
    
    # Step 3: Display results
    print("=" * 60)
    print("DETECTION RESULTS")
    print("=" * 60)
    print()
    
    if result["intruder_detected"]:
        print("🚨 INTRUDER DETECTED!")
        print()
        print(f"Detection Count: {result['detection_count']}")
        print(f"Alert ID: {result['alert_id']}")
        print()
        print("Detections:")
        print("-" * 60)
        
        for i, detection in enumerate(result["detections"], 1):
            print(f"\nDetection #{i}:")
            print(f"  Class: {detection['class']}")
            print(f"  Confidence: {detection['confidence']:.2%}")
            print(f"  Bounding Box: {detection['bbox']}")
        
        print()
        print("✅ An alert has been created and Socket.IO event emitted")
        
    else:
        print("✅ No intruders detected")
        print()
        print("The image was analyzed successfully, but no humans were found.")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
