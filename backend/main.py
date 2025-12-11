from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
import socketio

# Load environment variables
load_dotenv()

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-min-32-characters-long-for-hs256-algorithm")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 30
# CORS Configuration
# We use allow_origin_regex for Codespaces and allow_origins for local dev
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,https://congenial-waddle-v7q6v565x7ghppvg-5173.app.github.dev").split(",")

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# Socket.IO setup
# Allow all origins for Socket.IO in development to avoid CORS issues
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
# We will mount this later. Note: socketio_path="" because we mount at /socket.io
socket_app = socketio.ASGIApp(sio, socketio_path="")

# FastAPI app
app = FastAPI(title='SenseGrid API', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.app\.github\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (replace with database in production)
users_db: Dict[str, dict] = {}
rooms_db: Dict[str, list] = {}  # userId -> [rooms]
alerts_db: Dict[str, list] = {}  # homeId -> [alerts]


# Models
class UserRegister(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class CommandPayload(BaseModel):
    command: dict
    homeId: Optional[str] = None
    roomId: Optional[str] = None


class Room(BaseModel):
    roomId: str
    roomName: str
    deviceId: str
    sensors: dict
    actions: dict
    lastSeen: int


class Alert(BaseModel):
    alertId: str
    homeId: str
    snapshotUrl: str
    ts: int


class AlertAction(BaseModel):
    action: str  # 'allow' or 'deny'


# Auth utilities
def hash_password(password: str) -> str:
    # bcrypt has a 72-byte limit, so truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[dict]:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None or email not in users_db:
            raise HTTPException(status_code=401, detail="Invalid token")
        return users_db[email]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Health check
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# API Router
api = APIRouter(prefix="/api")


# Auth endpoints
@api.post('/auth/register')
async def register(user: UserRegister):
    if user.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = hash_password(user.password)
    user_data = {
        "email": user.email,
        "name": user.name,
        "password": hashed_pwd,
        "created_at": datetime.utcnow().isoformat()
    }
    users_db[user.email] = user_data
    rooms_db[user.email] = []
    
    token = create_access_token({"sub": user.email})
    return {
        "token": token,
        "user": {"name": user.name, "email": user.email}
    }


@api.post('/auth/login')
async def login(user: UserLogin):
    if user.email not in users_db:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    stored_user = users_db[user.email]
    if not verify_password(user.password, stored_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user.email})
    return {
        "token": token,
        "user": {"name": stored_user["name"], "email": stored_user["email"]}
    }


@api.get('/auth/me')
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"name": current_user["name"], "email": current_user["email"]}


# Room endpoints
@api.get('/rooms')
async def list_rooms(current_user: dict = Depends(get_current_user)):
    user_rooms = rooms_db.get(current_user["email"], [])
    if not user_rooms:
        # Return default room for new users
        default_room = {
            "roomId": "living-room",
            "roomName": "Living Room",
            "deviceId": "dev-living-room",
            "sensors": {"temperature": 22, "humidity": 45, "gas": 0, "flame": 0},
            "actions": {"temperature": "OFF"},
            "lastSeen": int(datetime.utcnow().timestamp() * 1000)
        }
        rooms_db[current_user["email"]] = [default_room]
        return [default_room]
    return user_rooms


@api.post('/rooms')
async def create_room(room: Room, current_user: dict = Depends(get_current_user)):
    user_rooms = rooms_db.get(current_user["email"], [])
    
    # Check if room already exists
    if any(r["roomId"] == room.roomId for r in user_rooms):
        raise HTTPException(status_code=400, detail="Room already exists")
    
    room_data = room.dict()
    user_rooms.append(room_data)
    rooms_db[current_user["email"]] = user_rooms
    
    return room_data


@api.post('/rooms/{room_id}/action')
async def room_action(room_id: str, payload: CommandPayload, current_user: dict = Depends(get_current_user)):
    cmd = payload.command or {}
    print(f"[backend] User {current_user['email']} - room action for room={room_id} cmd={cmd}")
    
    # Update room state in memory
    user_rooms = rooms_db.get(current_user["email"], [])
    for room in user_rooms:
        if room["roomId"] == room_id:
            sensor = cmd.get("sensor")
            value = cmd.get("value")
            if sensor and value:
                room["actions"][sensor] = value
            room["lastSeen"] = int(datetime.utcnow().timestamp() * 1000)
            
            # Emit socket update
            await sio.emit('sensorUpdate', {
                "roomId": room_id,
                "deviceId": room.get("deviceId"),
                "data": room
            }, room=current_user["email"])
            break
    
    return {"status": "ok", "roomId": room_id, "received": cmd}


@api.post('/devices/{device_id}/command')
async def device_command(device_id: str, payload: CommandPayload, current_user: dict = Depends(get_current_user)):
    cmd = payload.command or {}
    print(f"[backend] User {current_user['email']} - device command for device={device_id} cmd={cmd}")
    
    return {"status": "ok", "deviceId": device_id, "received": cmd}


@api.delete('/rooms/{room_id}')
async def delete_room(room_id: str, current_user: dict = Depends(get_current_user)):
    user_rooms = rooms_db.get(current_user["email"], [])
    rooms_db[current_user["email"]] = [r for r in user_rooms if r["roomId"] != room_id]
    print(f"[backend] User {current_user['email']} - deleted room {room_id}")
    return {"status": "ok", "roomId": room_id}


# Alert/Intruder endpoints
@api.get('/alerts')
async def list_alerts(homeId: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    if homeId:
        return alerts_db.get(homeId, [])
    # Return all alerts for user's homes
    all_alerts = []
    for alerts in alerts_db.values():
        all_alerts.extend(alerts)
    return all_alerts


@api.post('/alerts/{alert_id}/action')
async def alert_action(alert_id: str, payload: AlertAction, current_user: dict = Depends(get_current_user)):
    action = payload.action
    print(f"[backend] User {current_user['email']} - alert action for alert={alert_id} action={action}")
    
    # Remove alert from all homes after action
    for home_id, alerts in alerts_db.items():
        alerts_db[home_id] = [a for a in alerts if a.get("alertId") != alert_id]
    
    # Emit socket event to notify clients
    await sio.emit('alert:processed', {
        "alertId": alert_id,
        "action": action
    })
    
    return {"status": "ok", "alertId": alert_id, "action": action}


@api.post('/frontdoor/{alert_id}/{action}')
async def frontdoor_action(alert_id: str, action: str, current_user: dict = Depends(get_current_user)):
    print(f"[backend] User {current_user['email']} - frontdoor action for alert={alert_id} action={action}")
    
    # Remove alert from all homes after action
    for home_id, alerts in alerts_db.items():
        alerts_db[home_id] = [a for a in alerts if a.get("alertId") != alert_id]
    
    # Emit socket event to notify clients
    await sio.emit('alert:processed', {
        "alertId": alert_id,
        "action": action
    })
    
    return {"status": "ok", "alertId": alert_id, "action": action}


# Socket.IO events
@sio.event
async def connect(sid, environ):
    print(f"[socket.io] Client connected: {sid}")
    await sio.emit('connected', {'sid': sid}, room=sid)


@sio.event
async def disconnect(sid):
    print(f"[socket.io] Client disconnected: {sid}")


@sio.event
async def join_room(sid, data):
    room = data.get('room')
    if room:
        await sio.enter_room(sid, room)
        print(f"[socket.io] Client {sid} joined room {room}")


@sio.event
async def device_update(sid, data):
    """Handle device sensor updates from IoT devices"""
    device_id = data.get('deviceId')
    sensors = data.get('sensors', {})
    print(f"[socket.io] Device update from {device_id}: {sensors}")
    
    # Broadcast to all clients
    await sio.emit('sensorUpdate', {
        'deviceId': device_id,
        'sensors': sensors,
        'timestamp': datetime.utcnow().timestamp()
    })


@sio.event
async def intruder_alert(sid, data):
    """Handle intruder alert from security system"""
    alert_id = data.get('alertId')
    home_id = data.get('homeId')
    print(f"[socket.io] Intruder alert: {alert_id} for home {home_id}")
    
    # Store alert
    if home_id not in alerts_db:
        alerts_db[home_id] = []
    alerts_db[home_id].append(data)
    
    # Broadcast to all clients
    await sio.emit('intruder:alert', data)


app.include_router(api)

# Mount Socket.IO app
app.mount("/socket.io", socket_app)
