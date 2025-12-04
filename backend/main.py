from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title='SenseGrid API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CommandPayload(BaseModel):
    command: dict
    homeId: Optional[str] = None
    roomId: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


api = APIRouter(prefix="/api")


@api.post('/devices/{device_id}/command')
async def device_command(device_id: str, payload: CommandPayload):
    # Minimal handler to accept queued commands from the frontend offlineQueue
    cmd = payload.command or {}
    # Log to console so developers see activity
    print(f"[backend] received command for device={device_id} cmd={cmd}")
    return {"status": "ok", "deviceId": device_id, "received": cmd}


@api.post('/rooms/{room_id}/action')
async def room_action(room_id: str, payload: CommandPayload):
    cmd = payload.command or {}
    print(f"[backend] received room action for room={room_id} cmd={cmd}")
    return {"status": "ok", "roomId": room_id, "received": cmd}


@api.get('/rooms')
async def list_rooms():
    # Minimal static response so frontend can load something if needed
    return [{"roomId": "r1", "roomName": "Living Room", "deviceId": "d1", "sensors": {"temperature": 22, "humidity": 40}, "actions": {"temperature": "OFF"}, "lastSeen": 0}]


app.include_router(api)
