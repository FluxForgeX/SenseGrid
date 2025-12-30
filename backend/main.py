from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
import json
import os
from dotenv import load_dotenv
import socketio
import time
import tempfile

# Import database models and utilities
from database import User, Room as RoomDB, Alert as AlertDB, get_db, init_db

# Load environment variables
load_dotenv()

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-min-32-characters-long-for-hs256-algorithm")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 30

# CORS Configuration
# Supports: localhost, Codespaces, Raspberry Pi on local network
DEFAULT_CORS = "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174,http://localhost:3000"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", DEFAULT_CORS).split(",")

# Security
security = HTTPBearer(auto_error=False)

# Socket.IO setup
# Allow all origins for Socket.IO in development to avoid CORS issues
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# FastAPI app
app = FastAPI(title='SenseGrid API', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.app\.github\.dev|http://192\.168\.\d+\.\d+:\d+|http://10\.\d+\.\d+\.\d+:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables on startup
@app.on_event("startup")
async def startup_event():
    print("[startup] Initializing database...")
    init_db()
    print("[startup] Database initialized successfully")


# Pydantic Models for API
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


class RoomCreate(BaseModel):
    roomId: str
    roomName: str
    deviceId: str
    sensors: dict
    actions: dict
    lastSeen: int


class AlertCreate(BaseModel):
    alertId: str
    homeId: str
    snapshotUrl: Optional[str] = None
    ts: int


class AlertAction(BaseModel):
    action: str  # 'allow' or 'deny'


# Auth utilities
def hash_password(password: str) -> str:
    # bcrypt has a 72-byte limit, so truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    plain_bytes = plain.encode('utf-8')
    if len(plain_bytes) > 72:
        plain_bytes = plain_bytes[:72]
    try:
        return bcrypt.checkpw(plain_bytes, hashed.encode('utf-8'))
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Query user from database
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Helper functions for JSON serialization
def room_to_dict(room: RoomDB) -> dict:
    """Convert Room DB model to API response dict"""
    return {
        "roomId": room.room_id,
        "roomName": room.room_name,
        "deviceId": room.device_id,
        "sensors": json.loads(room.sensors) if room.sensors else {},
        "actions": json.loads(room.actions) if room.actions else {},
        "lastSeen": room.last_seen
    }


def alert_to_dict(alert: AlertDB) -> dict:
    """Convert Alert DB model to API response dict"""
    return {
        "alertId": alert.alert_id,
        "homeId": alert.home_id,
        "snapshotUrl": alert.snapshot_url,
        "ts": alert.timestamp,
        "resolved": alert.resolved
    }


# Health check
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# API Router
api = APIRouter(prefix="/api")


# Auth endpoints
@api.post('/auth/register')
async def register(user: UserRegister, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_pwd = hash_password(user.password)
    db_user = User(
        email=user.email,
        name=user.name,
        password=hashed_pwd
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create default room for new user
    default_room = RoomDB(
        room_id="living-room",
        room_name="Living Room",
        device_id="dev-living-room",
        sensors=json.dumps({"temperature": 22, "humidity": 45, "gas": 0, "flame": 0}),
        actions=json.dumps({"temperature": "OFF"}),
        last_seen=int(datetime.utcnow().timestamp() * 1000),
        user_id=db_user.id
    )
    db.add(default_room)
    db.commit()
    
    token = create_access_token({"sub": user.email})
    print(f"[register] New user created: {user.email}")
    return {
        "token": token,
        "user": {"name": user.name, "email": user.email}
    }


@api.post('/auth/login')
async def login(user: UserLogin, db: Session = Depends(get_db)):
    # Query user from database
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user.email})
    print(f"[login] User logged in: {user.email}")
    return {
        "token": token,
        "user": {"name": db_user.name, "email": db_user.email}
    }


@api.get('/auth/me')
async def get_me(current_user: User = Depends(get_current_user)):
    return {"name": current_user.name, "email": current_user.email}


# Room endpoints
@api.get('/rooms')
async def list_rooms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get user's rooms from database
    rooms = db.query(RoomDB).filter(RoomDB.user_id == current_user.id).all()
    
    if not rooms:
        # Create default room for new users
        default_room = RoomDB(
            room_id="living-room",
            room_name="Living Room",
            device_id="dev-living-room",
            sensors=json.dumps({"temperature": 22, "humidity": 45, "gas": 0, "flame": 0}),
            actions=json.dumps({"temperature": "OFF"}),
            last_seen=int(datetime.utcnow().timestamp() * 1000),
            user_id=current_user.id
        )
        db.add(default_room)
        db.commit()
        db.refresh(default_room)
        rooms = [default_room]
    
    return [room_to_dict(room) for room in rooms]


@api.post('/rooms')
async def create_room(
    room: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if room already exists for this user
    existing_room = db.query(RoomDB).filter(
        RoomDB.user_id == current_user.id,
        RoomDB.room_id == room.roomId
    ).first()
    
    if existing_room:
        raise HTTPException(status_code=400, detail="Room already exists")
    
    # Create new room
    db_room = RoomDB(
        room_id=room.roomId,
        room_name=room.roomName,
        device_id=room.deviceId,
        sensors=json.dumps(room.sensors),
        actions=json.dumps(room.actions),
        last_seen=room.lastSeen,
        user_id=current_user.id
    )
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    
    print(f"[rooms] User {current_user.email} created room: {room.roomId}")
    return room_to_dict(db_room)


@api.post('/rooms/{room_id}/action')
async def room_action(
    room_id: str,
    payload: CommandPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cmd = payload.command or {}
    print(f"[backend] User {current_user.email} - room action for room={room_id} cmd={cmd}")
    
    # Find room in database
    room = db.query(RoomDB).filter(
        RoomDB.user_id == current_user.id,
        RoomDB.room_id == room_id
    ).first()
    
    if room:
        sensor = cmd.get("sensor")
        value = cmd.get("value")
        
        if sensor and value:
            # Update actions
            actions = json.loads(room.actions) if room.actions else {}
            actions[sensor] = value
            room.actions = json.dumps(actions)
        
        room.last_seen = int(datetime.utcnow().timestamp() * 1000)
        db.commit()
        
        # Emit socket update
        await sio.emit('sensorUpdate', {
            "roomId": room_id,
            "deviceId": room.device_id,
            "data": room_to_dict(room)
        }, room=current_user.email)
    
    return {"status": "ok", "roomId": room_id, "received": cmd}


@api.post('/devices/{device_id}/command')
async def device_command(
    device_id: str,
    payload: CommandPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cmd = payload.command or {}
    print(f"[backend] User {current_user.email} - device command for device={device_id} cmd={cmd}")
    
    # Find room by device_id
    room = db.query(RoomDB).filter(
        RoomDB.user_id == current_user.id,
        RoomDB.device_id == device_id
    ).first()
    
    if room:
        sensor = cmd.get("sensor")
        value = cmd.get("value")
        
        if sensor and value:
            actions = json.loads(room.actions) if room.actions else {}
            actions[sensor] = value
            room.actions = json.dumps(actions)
            room.last_seen = int(datetime.utcnow().timestamp() * 1000)
            db.commit()
    
    return {"status": "ok", "deviceId": device_id, "received": cmd}


@api.delete('/rooms/{room_id}')
async def delete_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find and delete room
    room = db.query(RoomDB).filter(
        RoomDB.user_id == current_user.id,
        RoomDB.room_id == room_id
    ).first()
    
    if room:
        db.delete(room)
        db.commit()
        print(f"[backend] User {current_user.email} - deleted room {room_id}")
    
    return {"status": "ok", "roomId": room_id}


# Alert/Intruder endpoints
@api.get('/alerts')
async def list_alerts(
    homeId: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(AlertDB).filter(
        AlertDB.user_id == current_user.id,
        AlertDB.resolved == False
    )
    
    if homeId:
        query = query.filter(AlertDB.home_id == homeId)
    
    alerts = query.all()
    return [alert_to_dict(alert) for alert in alerts]


@api.post('/alerts/{alert_id}/action')
async def alert_action(
    alert_id: str,
    payload: AlertAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    action = payload.action
    print(f"[backend] User {current_user.email} - alert action for alert={alert_id} action={action}")
    
    # Find and resolve alert
    alert = db.query(AlertDB).filter(
        AlertDB.user_id == current_user.id,
        AlertDB.alert_id == alert_id
    ).first()
    
    if alert:
        alert.resolved = True
        db.commit()
    
    # Emit socket event to notify clients
    await sio.emit('alert:processed', {
        "alertId": alert_id,
        "action": action
    })
    
    return {"status": "ok", "alertId": alert_id, "action": action}


@api.post('/frontdoor/{alert_id}/{action}')
async def frontdoor_action(
    alert_id: str,
    action: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print(f"[backend] User {current_user.email} - frontdoor action for alert={alert_id} action={action}")
    
    # Find and resolve alert
    alert = db.query(AlertDB).filter(
        AlertDB.user_id == current_user.id,
        AlertDB.alert_id == alert_id
    ).first()
    
    if alert:
        alert.resolved = True
        db.commit()
    
    # Emit socket event to notify clients
    await sio.emit('alert:processed', {
        "alertId": alert_id,
        "action": action
    })
    
    return {"status": "ok", "alertId": alert_id, "action": action}


# Intruder detection endpoint
@api.post('/intruder/detect')
async def detect_intruder(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload an image for intruder detection.
    
    Uses configured detector (Roboflow Cloud API or local YOLO).
    Detector type is set via DETECTOR_TYPE environment variable.
    
    This endpoint:
    1. Accepts an uploaded image file
    2. Runs inference using configured detector
    3. Detects humans in the image
    4. Creates an alert if humans are detected
    5. Emits Socket.IO event to notify connected clients
    
    Returns:
        {
            "intruder_detected": bool,
            "detections": [{"class": "Human", "confidence": 0.87, "bbox": {...}}],
            "alert_id": str (if detected),
            "detector_type": str
        }
    """
    # Import and initialize detector lazily
    try:
        detector_type = os.getenv("DETECTOR_TYPE", "roboflow").lower()
        
        if detector_type in ("roboflow", "cloud"):
            from services.roboflow_detector import get_roboflow_detector
            detector = get_roboflow_detector()
        elif detector_type in ("local", "yolo"):
            from services.local_yolo_detector import get_detector
            detector = get_detector()
        else:
            raise ValueError(f"Unknown DETECTOR_TYPE: {detector_type}. Use 'roboflow' or 'local'")
            
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import detector: {str(e)}. Check dependencies in requirements.txt"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load intruder detector: {str(e)}"
        )
    
    # Save uploaded file to temporary location
    try:
        # Create temp file with correct extension
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        
        # Run detection using configured detector
        detections = detector.detect(temp_path, conf=0.5)
        
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(
            status_code=400,
            detail=f"Detection failed: {str(e)}"
        )
    finally:
        # Always clean up temp file
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
    
    # If humans detected, create alert and emit Socket.IO event
    alert_id = None
    if detections:
        alert_id = f"alert-{int(time.time() * 1000)}"
        
        # Save alert to database
        new_alert = AlertDB(
            alert_id=alert_id,
            home_id=current_user.email,  # Use email as home_id
            snapshot_url=None,  # Could save image to storage and set URL here
            timestamp=int(time.time() * 1000),
            resolved=False,
            user_id=current_user.id
        )
        db.add(new_alert)
        db.commit()
        
        # Emit Socket.IO event to notify clients
        await sio.emit('intruder:alert', {
            "alertId": alert_id,
            "homeId": current_user.email,
            "confidence": detections[0]["confidence"],
            "detectionCount": len(detections),
            "ts": int(time.time() * 1000)
        })
        
        # Build detection summary for log
        class_counts = {}
        for d in detections:
            cls = d.get("class", "Unknown")
            class_counts[cls] = class_counts.get(cls, 0) + 1
        summary = ", ".join(f"{count} {cls}" for cls, count in class_counts.items())
        print(f"[intruder] User {current_user.email} - detected {summary}, alert_id={alert_id}")
    
    return {
        "intruder_detected": len(detections) > 0,
        "detections": detections,
        "alert_id": alert_id,
        "detection_count": len(detections),
        "detector_type": detector_type
    }


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
    
    # Note: For socket events, we'd need to associate with a user
    # For now, just broadcast
    await sio.emit('intruder:alert', data)


app.include_router(api)

# Wrap FastAPI with Socket.IO ASGI app
# This ensures Socket.IO handles its own CORS and requests before they reach FastAPI
app = socketio.ASGIApp(sio, other_asgi_app=app)
