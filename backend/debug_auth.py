
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import os

# Configuration
JWT_SECRET = "dev-secret-key-min-32-characters-long-for-hs256-algorithm"
JWT_ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    print(f"Hashing password: {password}")
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    print(f"Creating token for: {data}")
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

try:
    print("Testing auth functions...")
    pwd = "testpassword123"
    hashed = hash_password(pwd)
    print(f"Hashed: {hashed}")
    
    token = create_access_token({"sub": "test@example.com"})
    print(f"Token: {token}")
    print("Auth functions working correctly.")
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
