# SenseGrid Project Documentation

## Overview
SenseGrid is a mobile-first Progressive Web App (PWA) for real-time control and monitoring of IoT room sensors. It features an offline-first architecture, optimistic UI updates, and robust device command queuing to ensure seamless user experience even during network disruptions.

The application is designed for home automation scenarios where users need to monitor and control multiple room sensors (temperature, humidity, gas, flame) and devices (fans, alerts) from a mobile device, with full functionality even when offline.

---

## Table of Contents
1. [Technologies Used](#technologies-used)
2. [Architecture](#architecture)
3. [Frontend](#frontend)
4. [Backend](#backend)
5. [Database & Migrations](#database--migrations)
6. [API Reference](#api-reference)
7. [Authentication & Security](#authentication--security)
8. [Environment Variables](#environment-variables)
9. [Sensor Thresholds & Auto-Actions](#sensor-thresholds--auto-actions)
10. [Offline Queue Pattern](#offline-queue-pattern)
11. [Real-time Updates](#real-time-updates)
12. [State Management](#state-management)
13. [PWA & Service Worker](#pwa--service-worker)
14. [Component Architecture](#component-architecture)
15. [Development & Testing](#development--testing)
16. [Deployment](#deployment)
17. [Error Handling](#error-handling)
18. [Accessibility & UX](#accessibility--ux)
19. [File Structure](#file-structure)
20. [Troubleshooting](#troubleshooting)

---

## Technologies Used

### Frontend Stack
- **React 18.2.0** - Core UI library with hooks and context API
- **Vite 5.x** - Build tool and dev server (fast HMR)
- **Zustand 4.4.0** - Lightweight state management with localStorage persistence
- **Tailwind CSS 3.x** - Utility-first CSS framework
- **Socket.IO-client 4.8.1** - Real-time bidirectional communication
- **idb 7.1.1** - IndexedDB wrapper for offline queue persistence
- **Axios 1.4.0** - HTTP client with interceptors
- **Framer Motion 11.0.0** - Animation library
- **React Router DOM 6.20.0** - Client-side routing
- **React Toastify 9.1.1** - Toast notifications
- **React Icons 4.10.1** - Icon library
- **Vite PWA Plugin 0.18** - PWA and service worker generation

### Backend Stack
- **FastAPI 0.104.1** - Modern Python web framework
- **Uvicorn 0.23.0** - ASGI server with hot reload
- **Python-SocketIO 5.10.0** - Socket.IO server implementation
- **SQLAlchemy 2.0.23** - SQL toolkit and ORM
- **Alembic 1.12.1** - Database migration tool
- **Python-JOSE 3.3.0** - JWT token handling
- **bcrypt 4.0.0+** - Password hashing
- **python-dotenv 1.0.0** - Environment variable management

### Database & Storage
- **SQLite** - Default relational database (can be replaced with PostgreSQL/MySQL)
- **IndexedDB** - Browser-based offline storage for command queue
- **localStorage** - Zustand state persistence

### Development Tools
- **Autoprefixer & PostCSS** - CSS processing
- **Chrome DevTools Lighthouse** - PWA auditing
- **ARIA/WCAG 2.1** - Accessibility standards

---

## Architecture

### System Design Overview
SenseGrid follows a **3-tier architecture** with offline-first principles:

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   PWA Frontend  │◄────────┤   FastAPI       │◄────────┤   SQLite DB     │
│   (React)       │  HTTP   │   Backend       │  ORM    │   (SQLAlchemy)  │
│                 │  +      │                 │         │                 │
│  ┌───────────┐  │  WS     │  ┌───────────┐  │         │  - users        │
│  │IndexedDB  │  │         │  │Socket.IO  │  │         │  - rooms        │
│  │Queue      │  │         │  │Server     │  │         │  - alerts       │
│  └───────────┘  │         │  └───────────┘  │         └─────────────────┘
└─────────────────┘         └─────────────────┘
       │                            │
       │ Background Sync            │ IoT Device Updates
       └────────────────────────────┘
```

### Core Architectural Patterns

1. **Mobile-first PWA**
   - Responsive design starting at 375px width
   - Installable on mobile devices
   - Full offline functionality

2. **Offline-first Command Queue**
   - All device actions are queued in IndexedDB if network fails
   - Automatic retry logic with exponential backoff
   - Background sync when connection restored
   - Maximum 5 retries per command

3. **Real-time Updates (Socket.IO)**
   - Bidirectional WebSocket connection
   - Server emits `sensorUpdate` events on state changes
   - Client listens and updates Zustand store → UI re-renders
   - Non-blocking: app works fully offline without socket connection

4. **Optimistic UI**
   - UI updates immediately on user action (before server confirmation)
   - Rollback on error with toast notification
   - Visual indicators: loading spinner → success/queued badge

5. **State Management (Zustand)**
   - Global app state with localStorage persistence
   - Middleware: persist (saves to localStorage)
   - Pattern: `updateRoom(roomId, patch)` for partial updates

### Data Flow

**User Action → Backend:**
```
User clicks toggle → Optimistic UI update → API call
                                             ↓ success
                                          Update store → Done
                                             ↓ failure
                                          Enqueue to IndexedDB → Show "Queued"
                                             ↓ online
                                          Background flush → Retry API
```

**Sensor Update → Frontend:**
```
IoT Device → Backend → Socket.IO emit('sensorUpdate')
                         ↓
            Frontend SocketProvider receives event
                         ↓
            Update Zustand store (updateRoom)
                         ↓
            RoomCard re-renders with new sensor data
```

---

## Frontend

### Location
`frontend/`

### Build Configuration
- **Dev Server:** Vite on `http://localhost:5173` (port 5174 fallback)
- **Build Output:** `frontend/dist/`
- **Environment Files:** `.env`, `.env.local`, `.env.production`

### Key Features
1. **Room and Sensor Grid UI**
   - Mobile-responsive card layout
   - Real-time sensor value display (temperature, humidity, gas, flame)
   - Device action controls (fan toggle, etc.)

2. **Optimistic Device Control**
   - Instant UI feedback on toggle
   - Loading states and error handling
   - Manual override tracking (5-minute window)

3. **Offline Queue Management**
   - IndexedDB-backed command persistence
   - Visual "Queued" badge on pending commands
   - Auto-flush when network restored

4. **Real-time Sensor Updates**
   - Socket.IO integration via `SocketProvider` context
   - Automatic reconnection on disconnect
   - Event handlers for `sensorUpdate`, `intruder:alert`

5. **PWA Features**
   - Install prompt (`useInstallPrompt` hook)
   - Service worker with network-first caching
   - Background sync for offline queue

6. **Accessibility**
   - ARIA labels on all interactive elements
   - Keyboard navigation support (Tab, Enter, Space)
   - Screen reader announcements for state changes
   - High contrast mode compatible

### Main Files

#### Components (`src/components/`)
- **`RoomCard.jsx`** - Core room control panel with optimistic UI pattern (333 lines)
  - Handles sensor display and action toggles
  - Implements offline queue integration
  - Manages manual override state
  
- **`RoomGrid.jsx`** - Grid layout for multiple room cards
  - Responsive grid (1 col mobile, 2+ desktop)
  - Socket.IO context consumer

- **`ActionToggle.jsx`** - Reusable toggle switch component
  - ON/OFF states with loading indicator
  - Queued badge when offline
  
- **`NotificationBell.jsx`** - Alert notification icon
  - Badge count for unread alerts
  - Click to show alert modal

- **`IntruderModal.jsx`** - Modal for intruder alerts
  - Allow/Deny actions
  - Snapshot image display

#### Services (`src/services/`)
- **`offlineQueue.js`** - IndexedDB-backed command queue (226 lines)
  - Methods: `enqueue()`, `flushQueue()`, `getStats()`
  - Event emitter for queue changes
  - Retry logic with exponential backoff
  
- **`api.js`** - Axios HTTP client (114 lines)
  - Base URL: `VITE_API_URL` or `http://localhost:8000/api`
  - Request interceptor: injects JWT token
  - Response interceptor: handles 401 errors
  - Functions: `fetchRooms()`, `postRoomAction()`, `sendDeviceCommand()`

- **`socket.jsx`** - Socket.IO client wrapper
  - `SocketProvider` context component
  - `useSocket()` hook for event subscriptions
  - Auto-reconnect on disconnect

#### Hooks (`src/hooks/`)
- **`useAutoActions.js`** - Auto-action threshold evaluation
  - Checks temperature, gas, humidity, flame thresholds
  - Respects manual override window
  - Triggers fan ON when conditions met

- **`useOnlineStatus.js`** - Network status monitoring
  - Returns `isOnline` boolean
  - Listens to `online`/`offline` events

- **`useInstallPrompt.js`** - PWA install prompt handler
  - Captures `beforeinstallprompt` event
  - Provides `showPrompt()` function

#### Store (`src/store/`)
- **`useStore.js`** - Zustand state management
  - State shape:
    ```javascript
    {
      user: { name, email },
      isAuthenticated: boolean,
      rooms: [{ roomId, deviceId, sensors, actions, ... }]
    }
    ```
  - Actions: `login()`, `logout()`, `setRooms()`, `updateRoom()`, `updateRoomAction()`
  - Persistence: localStorage via `persist` middleware

#### Pages (`src/pages/`)
- **`Dashboard.jsx`** - Main app view (logged-in users)
- **`LoginPage.jsx`** - User login form
- **`RegisterPage.jsx`** - User registration form
- **`LandingPage.jsx`** - Public homepage
- **`OnboardingPage.jsx`** - First-time user setup

### Frontend Dependencies
```json
{
  "axios": "^1.4.0",           // HTTP client
  "framer-motion": "^11.0.0",  // Animations
  "idb": "^7.1.1",             // IndexedDB wrapper
  "react": "^18.2.0",          // Core library
  "react-dom": "^18.2.0",      // DOM renderer
  "react-icons": "^4.10.1",    // Icon components
  "react-router-dom": "^6.20.0", // Routing
  "react-toastify": "^9.1.1",  // Toast notifications
  "recharts": "^2.6.2",        // Charts (future analytics)
  "socket.io-client": "^4.8.1", // Real-time connection
  "zustand": "^4.4.0"          // State management
}
```

---

## Backend

### Location
`backend/`

### Framework & Server
- **FastAPI 0.104.1** - Modern async Python web framework
- **Uvicorn 0.23.0** - ASGI server with hot reload
- **Server Address:** `http://127.0.0.1:8000` (dev), configurable for production

### Key Features
1. **REST API** for room/device control
2. **Socket.IO Server** for real-time bidirectional communication
3. **JWT Authentication** with bcrypt password hashing
4. **SQLite Database** via SQLAlchemy ORM
5. **CORS Configuration** supporting localhost, Codespaces, and Raspberry Pi local network
6. **Health Check Endpoint** at `/health`

### Main Files

#### `main.py` (520 lines)
Core application with FastAPI app, endpoints, Socket.IO events, and auth utilities.

**Configuration:**
```python
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-min-32-characters-long...")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 30

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,...").split(",")
```

**Socket.IO Setup:**
```python
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = socketio.ASGIApp(sio, other_asgi_app=app)
```

**Auth Utilities:**
- `hash_password(password: str) -> str` - bcrypt hashing (72-byte truncation)
- `verify_password(plain: str, hashed: str) -> bool` - Verify password
- `create_access_token(data: dict) -> str` - Generate JWT token
- `get_current_user(...) -> User` - Dependency for protected routes

**Helper Functions:**
- `room_to_dict(room: RoomDB) -> dict` - Convert DB model to API response
- `alert_to_dict(alert: AlertDB) -> dict` - Convert alert model to response

#### `database.py` (69 lines)
SQLAlchemy models and database session management.

**Database URL:**
```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sensegrid.db")
```

**Models:**
- **User** - `id`, `email` (unique), `name`, `password`, `created_at`
  - Relationships: `rooms`, `alerts`
- **Room** - `id`, `room_id`, `room_name`, `device_id`, `sensors` (JSON), `actions` (JSON), `last_seen`, `user_id`
  - Relationships: `user`
- **Alert** - `id`, `alert_id`, `home_id`, `snapshot_url`, `timestamp`, `resolved`, `user_id`
  - Relationships: `user`

**Functions:**
- `init_db()` - Create all tables (called on app startup)
- `get_db()` - Dependency for database session

#### `requirements.txt`
```
fastapi==0.104.1
uvicorn[standard]==0.23.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
bcrypt>=4.0.0
python-dotenv==1.0.0
python-socketio==5.10.0
aiofiles==23.2.1
sqlalchemy==2.0.23
alembic==1.12.1
```

### Backend Startup
```bash
cd backend
python -m venv .venv311
source .venv311/bin/activate  # Linux/Mac
# OR
.venv311\Scripts\activate     # Windows

pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

On startup, the app:
1. Loads environment variables from `.env`
2. Initializes database (creates tables if not exist)
3. Configures CORS middleware
4. Starts Socket.IO server
5. Mounts API router at `/api`

---

## Database & Migrations

### Default Database
- **Engine:** SQLite
- **File Location:** `backend/sensegrid.db`
- **ORM:** SQLAlchemy 2.0.23

### Database Schema

#### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### Rooms Table
```sql
CREATE TABLE rooms (
    id INTEGER PRIMARY KEY,
    room_id VARCHAR(255) NOT NULL,
    room_name VARCHAR(255),
    device_id VARCHAR(255),
    sensors TEXT,           -- JSON: {"temperature": 22, "humidity": 45, ...}
    actions TEXT,           -- JSON: {"fan": "ON", ...}
    last_seen INTEGER,      -- Unix timestamp (milliseconds)
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Alerts Table
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    alert_id VARCHAR(255) NOT NULL,
    home_id VARCHAR(255) NOT NULL,
    snapshot_url VARCHAR(512),
    timestamp INTEGER,      -- Unix timestamp (milliseconds)
    resolved BOOLEAN DEFAULT 0,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### Schema Migrations with Alembic

#### Setup Alembic (one-time)
```bash
cd backend
pip install alembic
alembic init alembic
```

Edit `alembic.ini`:
```ini
sqlalchemy.url = sqlite:///./sensegrid.db
```

Edit `alembic/env.py`:
```python
from database import Base
target_metadata = Base.metadata
```

#### Create Migration
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new column to rooms"

# Or create empty migration
alembic revision -m "Custom migration"
```

#### Apply Migrations
```bash
# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Check current version
alembic current

# View migration history
alembic history
```

### Development Mode
In development, the app auto-creates tables on startup via `init_db()` called in the `startup_event` handler. This is sufficient for local development but NOT recommended for production.

**Production:** Use Alembic for controlled schema migrations.

### Switching to PostgreSQL
1. Install PostgreSQL driver:
   ```bash
   pip install psycopg2-binary
   ```

2. Update `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/sensegrid
   ```

3. Run migrations:
   ```bash
   alembic upgrade head
   ```

---

## API Reference

### Base URL
- **Development:** `http://localhost:8000/api`
- **Production:** Set via `VITE_API_URL` environment variable

### Authentication Headers
All protected endpoints require JWT token in Authorization header:
```
Authorization: Bearer <jwt_token>
```

---

### Auth Endpoints

#### POST `/api/auth/register`
Register a new user and get JWT token.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

**Errors:**
- `400` - Email already registered

---

#### POST `/api/auth/login`
Login and get JWT token.

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

**Errors:**
- `401` - Invalid credentials

---

#### GET `/api/auth/me`
Get current user info (requires auth).

**Response (200 OK):**
```json
{
  "name": "John Doe",
  "email": "john@example.com"
}
```

**Errors:**
- `401` - Not authenticated or invalid token

---

### Room Endpoints

#### GET `/api/rooms`
List all rooms for authenticated user.

**Response (200 OK):**
```json
[
  {
    "roomId": "living-room",
    "roomName": "Living Room",
    "deviceId": "dev-living-room",
    "sensors": {
      "temperature": 24,
      "humidity": 45,
      "gas": 0,
      "flame": 0
    },
    "actions": {
      "fan": "OFF"
    },
    "lastSeen": 1735574400000
  }
]
```

If user has no rooms, creates a default "Living Room" automatically.

---

#### POST `/api/rooms`
Create a new room.

**Request Body:**
```json
{
  "roomId": "bedroom",
  "roomName": "Bedroom",
  "deviceId": "dev-bedroom",
  "sensors": {
    "temperature": 22,
    "humidity": 50,
    "gas": 0,
    "flame": 0
  },
  "actions": {
    "fan": "OFF"
  },
  "lastSeen": 1735574400000
}
```

**Response (200 OK):**
```json
{
  "roomId": "bedroom",
  "roomName": "Bedroom",
  "deviceId": "dev-bedroom",
  "sensors": {...},
  "actions": {...},
  "lastSeen": 1735574400000
}
```

**Errors:**
- `400` - Room already exists

---

#### POST `/api/rooms/{roomId}/action`
**PRIMARY ENDPOINT** for device control. Send a command to a specific room.

**Request Body:**
```json
{
  "command": {
    "sensor": "fan",
    "action": "set",
    "value": "ON"
  },
  "homeId": "home-123",
  "roomId": "living-room"
}
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "roomId": "living-room",
  "received": {
    "sensor": "fan",
    "action": "set",
    "value": "ON"
  }
}
```

**Behavior:**
- Updates room's `actions` JSON in database
- Emits Socket.IO `sensorUpdate` event to connected clients
- Updates `lastSeen` timestamp

**Usage from Frontend:**
```javascript
import { postRoomAction } from './services/api'

try {
  await postRoomAction('living-room', { sensor: 'fan', action: 'set', value: 'ON' })
  toast.success('Fan turned ON')
} catch (err) {
  // Fallback: enqueue to offline queue
  await offlineQueue.enqueue({ deviceId, command, homeId })
  toast.info('Command queued (offline)')
}
```

---

#### POST `/api/devices/{deviceId}/command`
Fallback endpoint for device-wide commands.

**Request Body:**
```json
{
  "command": {
    "sensor": "fan",
    "action": "set",
    "value": "OFF"
  },
  "homeId": "home-123",
  "roomId": "living-room"
}
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "deviceId": "dev-living-room",
  "received": {...}
}
```

---

#### DELETE `/api/rooms/{roomId}`
Delete a room.

**Response (200 OK):**
```json
{
  "status": "ok",
  "roomId": "living-room"
}
```

---

### Alert/Intruder Endpoints

#### GET `/api/alerts`
Get unresolved alerts for authenticated user.

**Query Parameters:**
- `homeId` (optional) - Filter by home ID

**Response (200 OK):**
```json
[
  {
    "alertId": "alert-001",
    "homeId": "home-123",
    "snapshotUrl": "https://example.com/snapshot.jpg",
    "ts": 1735574400000,
    "resolved": false
  }
]
```

---

#### POST `/api/alerts/{alertId}/action`
Resolve an alert (mark as resolved).

**Request Body:**
```json
{
  "action": "allow"  // or "deny"
}
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "alertId": "alert-001",
  "action": "allow"
}
```

**Behavior:**
- Marks alert as `resolved = true` in database
- Emits Socket.IO `alert:processed` event

---

#### POST `/api/frontdoor/{alertId}/{action}`
Legacy endpoint for front door alerts (allow/deny).

**Parameters:**
- `alertId` - Alert ID
- `action` - `allow` or `deny`

**Response (200 OK):**
```json
{
  "status": "ok",
  "alertId": "alert-001",
  "action": "allow"
}
```

---

### Health Check

#### GET `/health`
Check server status.

**Response (200 OK):**
```json
{
  "status": "ok",
  "timestamp": "2025-12-30T10:30:00.000000"
}
```

---

### Socket.IO Events

#### Client → Server

**`join_room`**
Join a Socket.IO room for targeted updates.
```javascript
socket.emit('join_room', { room: 'user@example.com' })
```

**`device_update`** (from IoT devices)
Report sensor updates from IoT hardware.
```javascript
socket.emit('device_update', {
  deviceId: 'dev-living-room',
  sensors: { temperature: 25, humidity: 48 }
})
```

**`intruder_alert`** (from security system)
Report intruder detection.
```javascript
socket.emit('intruder_alert', {
  alertId: 'alert-123',
  homeId: 'home-001',
  snapshotUrl: 'https://...'
})
```

---

#### Server → Client

**`connected`**
Sent when client connects.
```javascript
socket.on('connected', (data) => {
  console.log('Connected with sid:', data.sid)
})
```

**`sensorUpdate`**
Sensor state changed (emitted after room action or device update).
```javascript
socket.on('sensorUpdate', (data) => {
  // data = { roomId, deviceId, data: { roomId, sensors, actions, ... } }
  updateRoom(data.roomId, data.data)
})
```

**`intruder:alert`**
New intruder alert detected.
```javascript
socket.on('intruder:alert', (data) => {
  // data = { alertId, homeId, snapshotUrl, ts }
  showIntruderModal(data)
})
```

**`alert:processed`**
Alert was resolved.
```javascript
socket.on('alert:processed', (data) => {
  // data = { alertId, action }
  removeAlert(data.alertId)
})
```

---

## Authentication & Security

### JWT Token System
- **Algorithm:** HS256 (HMAC with SHA-256)
- **Expiration:** 30 days from issuance
- **Secret:** Configured via `JWT_SECRET` environment variable (minimum 32 characters)
- **Payload:** `{ sub: <user_email>, exp: <timestamp> }`

### Password Security
- **Hashing:** bcrypt with auto-generated salt
- **Truncation:** Passwords truncated to 72 bytes (bcrypt limit)
- **Validation:** Case-sensitive, no length restrictions

### Token Flow
1. User registers/logs in → Backend generates JWT
2. Frontend stores token in localStorage (`authToken`)
3. Axios interceptor injects token in Authorization header
4. Backend validates token on protected routes via `get_current_user()` dependency
5. On 401 error, frontend clears state and redirects to login

### CORS Configuration
Backend allows requests from:
- `http://localhost:5173`, `http://localhost:5174` (Vite dev)
- `http://localhost:3000` (alternative)
- `http://127.0.0.1:*` (localhost)
- GitHub Codespaces: `https://*.app.github.dev`
- Raspberry Pi local network: `http://192.168.*.*:*`, `http://10.*.*.*:*`

Configure additional origins via `CORS_ORIGINS` environment variable (comma-separated).

### Security Best Practices
1. **Never commit `.env` files** - Add to `.gitignore`
2. **Use strong JWT_SECRET** in production (generate with `openssl rand -hex 32`)
3. **Enable HTTPS** in production (use reverse proxy like Nginx with Let's Encrypt)
4. **Rate limiting** - Add rate limiting middleware (e.g., slowapi) for auth endpoints
5. **SQL injection prevention** - SQLAlchemy ORM handles parameterized queries
6. **XSS prevention** - React escapes JSX by default
7. **CSRF protection** - Not needed for JWT-based API (no cookies)

---

## Environment Variables

### Frontend (`.env` in `frontend/`)
```bash
# API Base URL (required)
VITE_API_URL=http://localhost:8000/api

# Socket.IO URL (optional, defaults to API_URL)
VITE_SOCKET_URL=http://localhost:8000
```

**Note:** Vite exposes variables prefixed with `VITE_` to the client bundle. Access via `import.meta.env.VITE_API_URL`.

### Backend (`.env` in `backend/`)
```bash
# JWT Secret (required, min 32 chars)
JWT_SECRET=your-secure-random-string-min-32-characters-long

# Database URL (optional, defaults to SQLite)
DATABASE_URL=sqlite:///./sensegrid.db
# For PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/sensegrid

# CORS Origins (optional, comma-separated)
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://192.168.1.100:5173

# Environment (optional)
ENVIRONMENT=development  # or production
```

### Production Environment Variables
For production deployment (e.g., Docker, Heroku, VPS):

```bash
# Frontend
VITE_API_URL=https://api.sensegrid.example.com

# Backend
JWT_SECRET=<generate with: openssl rand -hex 32>
DATABASE_URL=postgresql://user:password@db-host:5432/sensegrid
CORS_ORIGINS=https://sensegrid.example.com,https://www.sensegrid.example.com
ENVIRONMENT=production
```

---

## Sensor Thresholds & Auto-Actions

### Threshold Constants
Defined in `frontend/src/constants.js`:

```javascript
// Temperature threshold (°C)
export const TEMPERATURE_LIMIT = 35

// Gas threshold (ppm)
export const GAS_LIMIT = 350

// Humidity threshold (%)
export const HUMIDITY_LIMIT = 70

// Manual override timeout (milliseconds)
export const MANUAL_OVERRIDE_TIMEOUT = 5 * 60 * 1000  // 5 minutes

// Max retries for queued commands
export const MAX_QUEUE_RETRIES = 5
```

### Auto-Action Logic
Implemented in `frontend/src/hooks/useAutoActions.js`. Evaluates sensor readings and triggers fan automatically when:

1. **Temperature > 35°C** → Turn fan ON
2. **Gas > 350 ppm** → Turn fan ON  
3. **Flame detected (value = 1)** → Turn fan ON
4. **Humidity > 70%** → Turn fan ON (optional)

### Manual Override System
When user manually toggles a device, a 5-minute "manual override window" is activated:

```javascript
updateRoom(roomId, { 
  manualOverrideUntil: Date.now() + MANUAL_OVERRIDE_TIMEOUT 
})
```

During this window, auto-actions are paused to respect user's explicit control.

### Auto-Action Flow
```
Sensor update received
  ↓
evaluateAutoActions() called
  ↓
Check if manual override active (now < manualOverrideUntil)
  ↓ No override
Check threshold conditions (temp, gas, flame, humidity)
  ↓ Condition met
Check if fan already ON
  ↓ Fan OFF
Generate command: { action: 'set', target: 'fan', value: 'ON' }
  ↓
Optimistic update: set fan to ON in UI
  ↓
Try sendDeviceCommand()
  ↓ Success          ↓ Failure
Update state      Enqueue to offline queue
Show success      Show "Queued" badge
```
- **Service:** `frontend/src/services/offlineQueue.js`
- **Pattern:**
---

## Offline Queue Pattern

### Overview
The offline queue is the **core integration pattern** for all device commands. It ensures reliable command delivery even when network connectivity is intermittent.

### Service Location
`frontend/src/services/offlineQueue.js` (226 lines)

### Architecture
- **Storage:** IndexedDB (via `idb` library)
- **Database Name:** `sensegrid-offline-db`
- **Store Name:** `commands`
- **Indexes:** `by-device`, `by-status`

### Queue Item Schema
```javascript
{
  id: "cmd_1735574400000_xyz123",      // Unique ID
  deviceId: "dev-living-room",         // Target device
  command: {                            // Command payload
    sensor: "fan",
    action: "set",
    value: "ON"
  },
  homeId: "home-123",                   // Home/user ID
  roomId: "living-room",                // Room ID
  status: "pending",                    // "pending" | "flushing" | "failed"
  retries: 0,                           // Retry count
  maxRetries: 5,                        // Max retry attempts
  createdAt: 1735574400000,            // Creation timestamp
  lastRetryAt: null                     // Last retry timestamp
}
```

### API Methods

#### `enqueue(item)`
Add a command to the queue.
```javascript
const itemId = await offlineQueue.enqueue({
  deviceId: 'dev-living-room',
  command: { sensor: 'fan', action: 'set', value: 'ON' },
  homeId: 'home-123',
  roomId: 'living-room'
})
```

#### `flushQueue()`
Attempt to sync all pending items with the server.
```javascript
await offlineQueue.flushQueue()
```

#### `list()`
Get all queued items.
```javascript
const items = await offlineQueue.list()
```

#### `isQueuedFor(deviceId, sensor)`
Check if a specific sensor has pending commands.
```javascript
const isQueued = await offlineQueue.isQueuedFor('dev-living-room', 'fan')
```

#### `getQueuedItemsFor(deviceId)`
Get all pending items for a specific device.
```javascript
const items = await offlineQueue.getQueuedItemsFor('dev-living-room')
```

#### `remove(id)`
Remove a specific item from the queue.
```javascript
await offlineQueue.remove('cmd_123')
```

#### `clear()`
Clear entire queue (dangerous - for debugging only).
```javascript
await offlineQueue.clear()
```

#### `getStats()`
Get queue statistics.
```javascript
const stats = await offlineQueue.getStats()
// { total: 3, pending: 2, failed: 1, oldestItem: {...} }
```

### Event Emitter
Subscribe to queue events:

```javascript
// Listen for enqueue events
const unsubscribe = offlineQueue.subscribe('enqueued', ({ item }) => {
  console.log('Item queued:', item.id)
})

// Listen for flush events
offlineQueue.subscribe('flushed', ({ id, success }) => {
  if (success) {
    toast.success('Command synced!')
  }
})

// Clean up
unsubscribe()
```

**Events:**
- `enqueued` - Item added to queue
- `flushing` - Flush started
- `flushed` - Item successfully synced (or failed after max retries)

### Usage Pattern in Components
Example from `RoomCard.jsx`:

```javascript
async function handleToggle(sensor, value) {
  const command = { sensor, action: 'set', value }
  
  // 1. Optimistic update
  setRoomState(prev => ({
    ...prev,
    actions: { ...prev.actions, [sensor]: value }
  }))
  
  // 2. Try API call
  try {
    await postRoomAction(roomId, command, homeId)
    toast.success(`${sensor} set to ${value}`)
  } catch (err) {
    // 3. Enqueue on failure
    await offlineQueue.enqueue({
      deviceId: room.deviceId,
      command,
      homeId,
      roomId
    })
    toast.info('Command queued (offline)')
  }
}
```

### Auto-Flush Behavior
- Automatically flushes on `enqueue()` if `navigator.onLine === true`
- Service worker triggers background sync on `online` event
- Manual flush available: `offlineQueue.flushQueue()`

### Retry Logic
- Max retries: 5 (configurable via `MAX_QUEUE_RETRIES` constant)
- Exponential backoff: 1s, 2s, 4s, 8s, 16s
- After max retries, item status set to `"failed"`
- Failed items remain in queue for manual inspection/retry

### Debugging Commands
Open browser console (F12) and run:

```javascript
// Get queue stats
await offlineQueue.getStats()

// List all items
await offlineQueue.list()

// Clear queue (caution!)
await offlineQueue.clear()

// Manually flush
await offlineQueue.flushQueue()

// Check if sensor queued
await offlineQueue.isQueuedFor('dev-living-room', 'fan')
```

See `OFFLINE_QUEUE.md` for complete debugging reference.

---

## Real-time Updates

### Socket.IO Integration
Used for bidirectional, event-based communication between backend and frontend.

### Frontend Setup
Located in `frontend/src/services/socket.jsx`:

```javascript
import { io } from 'socket.io-client'
import { createContext, useContext } from 'react'

const SocketContext = createContext()

export function SocketProvider({ children }) {
  const socket = io(VITE_SOCKET_URL || 'http://localhost:8000', {
    autoConnect: true,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 10
  })
  
  return (
    <SocketContext.Provider value={socket}>
      {children}
    </SocketContext.Provider>
  )
}

export function useSocket() {
  return useContext(SocketContext)
}
```

### Usage in Components
Example from `RoomGrid.jsx`:

```javascript
import { useSocket } from '../services/socket'

function RoomGrid() {
  const socket = useSocket()
  const updateRoom = useStore(state => state.updateRoom)
  
  useEffect(() => {
    function handleSensorUpdate(data) {
      console.log('Sensor update:', data)
      if (data.roomId && data.data) {
        updateRoom(data.roomId, data.data)
      }
    }
    
    socket.on('sensorUpdate', handleSensorUpdate)
    socket.on('connect', () => console.log('Socket connected'))
    socket.on('disconnect', () => console.log('Socket disconnected'))
    
    return () => {
      socket.off('sensorUpdate', handleSensorUpdate)
    }
  }, [socket, updateRoom])
  
  // ... rest of component
}
```

### Backend Socket.IO Events
Defined in `backend/main.py`:

```python
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
    await sio.enter_room(sid, room)

@sio.event
async def device_update(sid, data):
    """IoT devices send sensor updates"""
    device_id = data.get('deviceId')
    sensors = data.get('sensors', {})
    await sio.emit('sensorUpdate', {
        'deviceId': device_id,
        'sensors': sensors
    })
```

### Connection Lifecycle
1. Client connects → `connect` event fired
2. Client joins room (optional): `socket.emit('join_room', { room: 'user@example.com' })`
3. Backend emits updates: `sio.emit('sensorUpdate', data)`
4. Client receives and processes: `socket.on('sensorUpdate', handler)`
5. Client disconnects → `disconnect` event fired

### Error Handling
- Socket connection is **non-blocking** - app works fully offline
- Auto-reconnection with exponential backoff (10 attempts, 1s delay)
- Graceful degradation: if socket fails, app continues using polling/queue

---

## State Management

### Zustand Store
Located in `frontend/src/store/useStore.js`.

### Store Structure
```javascript
{
  // Authentication
  user: { name: string, email: string } | null,
  isAuthenticated: boolean,
  
  // Rooms data
  rooms: [
    {
      roomId: string,
      roomName: string,
      deviceId: string,
      sensors: {
        temperature: number,
        humidity: number,
        gas: number,
        flame: number
      },
      actions: {
        fan: "ON" | "OFF"
      },
      lastSeen: number,
      manualOverrideUntil: number | undefined,
      queuedItems: array | undefined
    }
  ]
}
```

### Store Actions

#### Authentication
```javascript
const { login, logout, isAuthenticated } = useStore()

// Login user
login({ name: 'John Doe', email: 'john@example.com' })

// Logout user (clears all state)
logout()
```

#### Room Management
```javascript
const { rooms, setRooms, addRoom, removeRoom, updateRoom } = useStore()

// Set all rooms (from API)
setRooms([room1, room2, room3])

// Add a new room
addRoom({ roomId: 'bedroom', roomName: 'Bedroom', ... })

// Remove a room
removeRoom('bedroom')

// Update a room (partial update)
updateRoom('living-room', { 
  sensors: { temperature: 25 },
  lastSeen: Date.now()
})

// Update room action (optimistic UI)
updateRoomAction('living-room', 'fan', 'ON')
```

### Persistence
State persists to `localStorage` with key `sensegrid-storage` via Zustand's `persist` middleware:

```javascript
{
  name: 'sensegrid-storage',  // localStorage key
  storage: createJSONStorage(() => localStorage)
}
```

**Persisted fields:**
- `user`
- `isAuthenticated`  
- `rooms`

**Not persisted:**
- Transient UI state
- Socket connection state

### Usage in Components
```javascript
// Select specific slices
const rooms = useStore(state => state.rooms)
const updateRoom = useStore(state => state.updateRoom)

// Select with selector (prevents re-renders)
const livingRoom = useStore(state => 
  state.rooms.find(r => r.roomId === 'living-room')
)
```

---

## PWA & Service Worker

### Service Worker Generation
Auto-generated by Vite PWA plugin (configured in `vite.config.js`):

```javascript
VitePWA({
  registerType: 'autoUpdate',
  manifest: {
    name: 'SenseGrid',
    short_name: 'SenseGrid',
    start_url: '/',
    display: 'standalone',
    background_color: '#ffffff',
    theme_color: '#0ea5a4',
    icons: [
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' }
    ]
  },
  workbox: {
    runtimeCaching: [
      { urlPattern: /\/api\//, handler: 'NetworkFirst' },
      { urlPattern: /\/icons\//, handler: 'CacheFirst' }
    ]
  }
})
```

### Custom Service Worker
Located in `frontend/sw.js` for background sync.

**Responsibilities:**
- Cache API responses (NetworkFirst strategy)
- Cache static assets (CacheFirst strategy)
- Listen for `sync` event to flush offline queue
- Update app on new version available

### Caching Strategies

**NetworkFirst** (for API calls):
1. Try network request
2. If offline or timeout, serve from cache
3. Update cache with network response

**CacheFirst** (for static assets):
1. Check cache first
2. If not cached, fetch from network
3. Store in cache for future use

### Install Prompt
Hook in `frontend/src/hooks/useInstallPrompt.js`:

```javascript
export function useInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  
  useEffect(() => {
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault()
      setDeferredPrompt(e)
    })
  }, [])
  
  const showPrompt = async () => {
    if (!deferredPrompt) return
    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice
    setDeferredPrompt(null)
    return outcome
  }
  
  return { canInstall: !!deferredPrompt, showPrompt }
}
```

### PWA Requirements Checklist
✅ HTTPS (or localhost for dev)
✅ Web app manifest (`manifest.json`)
✅ Service worker registered
✅ Icons (192x192, 512x512)
✅ `start_url` defined
✅ `display: standalone`
✅ Offline page/functionality

### Testing PWA
```bash
# Build production bundle
npm run build

# Preview with service worker
npm run preview

# Open http://localhost:4173 in Chrome
# DevTools → Application → Manifest
# DevTools → Lighthouse → Run audit
```

**Lighthouse Audit Targets:**
- Performance: >90
- Accessibility: >90
- Best Practices: >90
- PWA: 100

---

## Component Architecture

### Component Hierarchy
```
App.jsx
├── Router
│   ├── LandingPage
│   ├── LoginPage
│   ├── RegisterPage
│   ├── OnboardingPage
│   └── Dashboard
│       ├── NotificationBell
│       │   └── IntruderModal
│       └── RoomGrid (wrapped in SocketProvider)
│           └── RoomCard[]
│               └── ActionToggle
```

### Design Patterns

#### 1. Container/Presentational Pattern
- **Container:** `RoomGrid` - manages state, Socket.IO, API calls
- **Presentational:** `RoomCard`, `ActionToggle` - pure UI, receives props

#### 2. Custom Hooks Pattern
- **`useSocket()`** - Socket.IO context consumer
- **`useOnlineStatus()`** - Network status
- **`useAutoActions()`** - Threshold evaluation logic
- **`useInstallPrompt()`** - PWA install prompt

#### 3. Optimistic UI Pattern
All user actions update UI immediately, before server response:
```javascript
// 1. Optimistic update
setLocalState(newValue)

// 2. API call
try {
  await api.call()
} catch {
  // 3. Revert on error
  setLocalState(oldValue)
  // Or enqueue to offline queue
}
```

#### 4. Compound Component Pattern
`IntruderModal` as compound component:
```jsx
<IntruderModal isOpen={open} onClose={handleClose}>
  <IntruderModal.Header>...</IntruderModal.Header>
  <IntruderModal.Body>...</IntruderModal.Body>
  <IntruderModal.Actions>...</IntruderModal.Actions>
</IntruderModal>
```

### Props Patterns

#### RoomCard Props
```typescript
interface RoomCardProps {
  room: Room           // Room data
  socket: Socket       // Socket.IO instance
  queuedItems?: array  // Queued commands (optional)
}
```

#### ActionToggle Props
```typescript
interface ActionToggleProps {
  sensor: string       // Sensor name ('fan', 'light')
  value: string        // Current value ('ON' | 'OFF')
  loading?: boolean    // Show loading spinner
  queued?: boolean     // Show queued badge
  disabled?: boolean   // Disable interaction
  onChange: (sensor, newValue) => void
}
```

---

## Component Architecture

### Responsive Design Breakpoints (Tailwind CSS)
```javascript
screens: {
  'sm': '640px',   // Mobile landscape / small tablets
  'md': '768px',   // Tablets
  'lg': '1024px',  // Desktop
  'xl': '1280px',  // Large desktop
  '2xl': '1536px'  // Extra large desktop
}
```

### Layout Strategy
1. **Base:** Single column, full width (mobile portrait)
2. **sm:** 2 columns for room grid
3. **md:** 3 columns, increased padding
4. **lg:** 4 columns, max-width container
5. **xl:** 5 columns (optional)

Example from `RoomGrid.jsx`:
```jsx
<div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 p-4">
  {rooms.map(room => <RoomCard key={room.roomId} room={room} />)}
</div>
```

---

## Development & Testing

### Development Environment Setup

#### Backend Setup
```bash
cd backend

# Create virtual environment (Python 3.11+)
python -m venv .venv311

# Activate virtual environment
# Linux/Mac:
source .venv311/bin/activate
# Windows:
.venv311\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start development server
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Backend runs on:** `http://127.0.0.1:8000`
**API docs (Swagger):** `http://127.0.0.1:8000/docs`
**Alternative docs (ReDoc):** `http://127.0.0.1:8000/redoc`

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server (Vite)
npm run dev
```

**Frontend runs on:** `http://localhost:5173` (or 5174 if 5173 is busy)

### Testing Strategies

#### 1. Manual Testing - Offline Queue
```
1. Open Chrome DevTools (F12)
2. Go to Network tab
3. Check "Offline" checkbox
4. Toggle any sensor in UI
5. Verify "Queued" badge appears
6. Open Console, run: await offlineQueue.getStats()
7. Uncheck "Offline"
8. Watch queue auto-flush
9. Verify badge disappears and toast shows "synced"
```

#### 2. Manual Testing - Real-time Updates
```
1. Open app in two browser windows (different accounts)
2. Login to same account in both
3. Toggle sensor in Window 1
4. Verify sensor updates instantly in Window 2 (via Socket.IO)
```

#### 3. Manual Testing - PWA Install
```
1. npm run build && npm run preview
2. Open http://localhost:4173 in Chrome
3. Look for install icon in address bar
4. Click install
5. Verify app opens in standalone window
6. Check app works offline
```

#### 4. Manual QA Checklist
- ✅ **Mobile emulation** (375px width) - Chrome DevTools
- ✅ **Tablet emulation** (768px width)
- ✅ **Desktop** (1920x1080)
- ✅ **Keyboard navigation** (Tab through all controls, Enter/Space to activate)
- ✅ **Screen reader** (NVDA on Windows, VoiceOver on Mac)
- ✅ **High contrast mode** (Windows: Alt+Shift+PrtScn)
- ✅ **Dark mode** (if implemented)
- ✅ **No console errors** in production build
- ✅ **Network throttling** (DevTools → Network → Slow 3G)
- ✅ **Lighthouse audit** (Performance >90, PWA = 100)

### Automated Testing (Future)

#### Unit Tests (Recommended)
```bash
# Install testing libraries
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom

# Run tests
npm test
```

Example test for `offlineQueue.js`:
```javascript
import { describe, it, expect } from 'vitest'
import offlineQueue from './offlineQueue'

describe('offlineQueue', () => {
  it('should enqueue an item', async () => {
    const id = await offlineQueue.enqueue({
      deviceId: 'test-device',
      command: { sensor: 'fan', value: 'ON' }
    })
    expect(id).toBeDefined()
  })
})
```

#### Integration Tests
```bash
# Install Playwright
npm install --save-dev @playwright/test

# Run E2E tests
npx playwright test
```

#### Backend Tests
```bash
cd backend
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

Example test:
```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

### Debugging

#### Frontend Debugging
1. **React DevTools:** Install Chrome extension
2. **Zustand DevTools:** Install Redux DevTools extension (Zustand compatible)
3. **Network Tab:** Monitor API calls, Socket.IO traffic
4. **Console Logging:**
   ```javascript
   console.log('[RoomCard] Rendering room:', room.roomId)
   ```

#### Backend Debugging
1. **FastAPI logs:** Check console output for `[backend]` prefixed logs
2. **Database inspection:**
   ```bash
   sqlite3 backend/sensegrid.db
   .tables
   SELECT * FROM users;
   SELECT * FROM rooms;
   ```
3. **API docs:** `http://127.0.0.1:8000/docs` for interactive testing

#### Common Issues & Solutions

**Issue:** CORS errors
**Solution:** Add your domain to `CORS_ORIGINS` in backend `.env`

**Issue:** JWT token invalid
**Solution:** Clear localStorage, re-login

**Issue:** Offline queue not flushing
**Solution:** Check `offlineQueue.getStats()`, verify `navigator.onLine === true`

**Issue:** Socket.IO not connecting
**Solution:** Check `VITE_SOCKET_URL`, verify backend running, check CORS

**Issue:** Python module import errors
**Solution:** Ensure virtual environment activated: `which python` should point to `.venv311/bin/python`

---

## Deployment

### Frontend Deployment (Vercel/Netlify)

#### Vercel
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel

# Set environment variable
vercel env add VITE_API_URL production
# Enter: https://api.sensegrid.example.com
```

**vercel.json:**
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "env": {
    "VITE_API_URL": "@vite_api_url"
  }
}
```

#### Netlify
```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
cd frontend
netlify deploy --prod

# Set environment variable
netlify env:set VITE_API_URL https://api.sensegrid.example.com
```

**netlify.toml:**
```toml
[build]
  command = "npm run build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

### Backend Deployment

#### Docker (Recommended)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - DATABASE_URL=postgresql://user:pass@db:5432/sensegrid
      - CORS_ORIGINS=https://sensegrid.example.com
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=sensegrid
    volumes:
      - db-data:/var/lib/postgresql/data

volumes:
  db-data:
```

**Build and run:**
```bash
docker-compose up -d
```

#### Heroku
```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login
heroku login

# Create app
heroku create sensegrid-backend

# Set environment variables
heroku config:set JWT_SECRET=<your-secret>
heroku config:set CORS_ORIGINS=https://sensegrid.example.com

# Deploy
git push heroku master
```

**Procfile:**
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

#### VPS (Ubuntu 22.04)
```bash
# SSH into VPS
ssh user@your-vps-ip

# Install Python and dependencies
sudo apt update
sudo apt install python3.11 python3.11-venv nginx certbot python3-certbot-nginx

# Clone repo
git clone https://github.com/ebrahim-77/SenseGrid.git
cd SenseGrid/backend

# Setup virtual environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create systemd service
sudo nano /etc/systemd/system/sensegrid.service
```

**sensegrid.service:**
```ini
[Unit]
Description=SenseGrid FastAPI App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/SenseGrid/backend
Environment="PATH=/home/ubuntu/SenseGrid/backend/.venv/bin"
ExecStart=/home/ubuntu/SenseGrid/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Start service
sudo systemctl start sensegrid
sudo systemctl enable sensegrid

# Configure Nginx reverse proxy
sudo nano /etc/nginx/sites-available/sensegrid
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name api.sensegrid.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Enable site and reload Nginx
sudo ln -s /etc/nginx/sites-available/sensegrid /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Setup SSL with Let's Encrypt
sudo certbot --nginx -d api.sensegrid.example.com
```

### Production Checklist
- ✅ Set strong `JWT_SECRET` (min 32 chars)
- ✅ Use PostgreSQL instead of SQLite
- ✅ Enable HTTPS (SSL/TLS certificates)
- ✅ Configure CORS for production domains only
- ✅ Set up database backups
- ✅ Configure logging (file rotation, error tracking)
- ✅ Enable rate limiting on auth endpoints
- ✅ Set up monitoring (Sentry, Datadog)
- ✅ Configure CDN for static assets
- ✅ Enable gzip/brotli compression
- ✅ Set up CI/CD pipeline (GitHub Actions)

---

## Error Handling

### Frontend Error Handling

#### Axios Interceptor (401 Errors)
Located in `frontend/src/services/api.js`:
```javascript
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('sensegrid-storage')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

#### API Error Handling Pattern
```javascript
try {
  await api.call()
  toast.success('Success!')
} catch (error) {
  if (error.response) {
    // Server responded with error status
    toast.error(error.response.data.detail || 'Server error')
  } else if (error.request) {
    // Request made but no response (network error)
    toast.error('Network error - check connection')
    // Enqueue to offline queue
    await offlineQueue.enqueue(...)
  } else {
    // Other errors (e.g., request setup)
    toast.error('Unexpected error occurred')
  }
}
```

#### Component Error Boundaries
```jsx
class ErrorBoundary extends React.Component {
  state = { hasError: false }
  
  static getDerivedStateFromError(error) {
    return { hasError: true }
  }
  
  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo)
  }
  
  render() {
    if (this.state.hasError) {
      return <div>Something went wrong. Please refresh.</div>
    }
    return this.props.children
  }
}

// Usage
<ErrorBoundary>
  <App />
</ErrorBoundary>
```

### Backend Error Handling

#### FastAPI Exception Handling
```python
from fastapi import HTTPException

# Raise HTTP exceptions
if not user:
    raise HTTPException(status_code=401, detail="Invalid credentials")

if room_exists:
    raise HTTPException(status_code=400, detail="Room already exists")
```

#### Global Exception Handler
```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

#### Database Error Handling
```python
from sqlalchemy.exc import IntegrityError

try:
    db.add(new_user)
    db.commit()
except IntegrityError:
    db.rollback()
    raise HTTPException(status_code=400, detail="Email already exists")
```

### Logging

#### Frontend Logging
```javascript
// Production: send to logging service (e.g., Sentry)
if (import.meta.env.PROD) {
  Sentry.captureException(error)
} else {
  console.error('[Component]', error)
}
```

#### Backend Logging
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"User {user.email} logged in")
logger.error(f"Failed to process command: {error}")
```

---

## Accessibility & UX

### WCAG 2.1 Compliance (Level AA)

#### Touch Targets
All interactive elements meet minimum size requirement:
- **Buttons:** 44x44px minimum (mobile)
- **Toggle switches:** 48x48px touch area
- **Links:** 44x44px (with padding if needed)

```css
/* Example from ActionToggle.jsx */
.toggle-button {
  min-width: 44px;
  min-height: 44px;
  padding: 12px;
}
```

#### Color Contrast
- **Normal text:** 4.5:1 minimum
- **Large text (18pt+):** 3:1 minimum
- **Interactive elements:** 3:1 for borders/icons

Tailwind CSS classes used:
- `text-gray-900` on `bg-white` - 21:1 ratio ✅
- `text-white` on `bg-teal-600` - 4.9:1 ratio ✅

#### Keyboard Navigation
All interactive elements accessible via keyboard:
- **Tab:** Move between focusable elements
- **Shift+Tab:** Move backward
- **Enter/Space:** Activate buttons, toggles
- **Escape:** Close modals

```jsx
// Example: Toggle with keyboard support
<button
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick()
    }
  }}
  aria-label={`Toggle ${sensor} ${value === 'ON' ? 'off' : 'on'}`}
>
```

#### ARIA Labels
All interactive elements have descriptive labels:

```jsx
// Button with ARIA label
<button aria-label="Delete room">
  <FaTrash />
</button>

// Toggle with state announcement
<button
  aria-label={`Fan is ${fanState}. Click to turn ${fanState === 'ON' ? 'off' : 'on'}.`}
  aria-pressed={fanState === 'ON'}
>

// Loading state announcement
<div
  role="status"
  aria-live="polite"
  aria-busy={loading}
>
  {loading ? 'Loading...' : 'Ready'}
</div>
```

#### Screen Reader Support
- **Live regions:** `aria-live="polite"` for toast notifications
- **Role annotations:** `role="button"`, `role="dialog"`, `role="alert"`
- **State announcements:** `aria-pressed`, `aria-expanded`, `aria-checked`
- **Landmarks:** `<main>`, `<nav>`, `<aside>`, `<header>`

#### Focus Management
```jsx
// Trap focus in modal
useEffect(() => {
  if (isOpen) {
    const firstFocusable = modalRef.current.querySelector('button')
    firstFocusable?.focus()
  }
}, [isOpen])

// Restore focus on close
const handleClose = () => {
  setIsOpen(false)
  previouslyFocusedElement?.focus()
}
```

### Mobile-First Design

#### Responsive Breakpoints
```javascript
// Tailwind breakpoints (mobile-first)
'sm': '640px',   // Small tablets
'md': '768px',   // Tablets
'lg': '1024px',  // Desktop
'xl': '1280px'   // Large desktop
```

#### Layout Patterns
```jsx
// Mobile: Single column
// Tablet: 2 columns
// Desktop: 4 columns
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
```

#### Touch Gestures
- **Tap:** Activate buttons, toggles
- **Long press:** (Future) Show context menu
- **Swipe:** (Future) Dismiss notifications

#### Viewport Meta Tag
```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

### UX Patterns

#### Optimistic UI Updates
Immediate visual feedback before server confirmation:
1. User taps toggle
2. Toggle switches instantly
3. Loading spinner appears (optional)
4. Server confirms or rejects
5. Final state shown (or reverted on error)

#### Loading States
```jsx
{loading && <Spinner />}
{queued && <Badge>Queued</Badge>}
{error && <ErrorIcon />}
```

#### Toast Notifications
Using `react-toastify`:
```javascript
toast.success('Fan turned ON')
toast.error('Failed to connect')
toast.info('Command queued (offline)')
toast.warning('High temperature detected')
```

**Position:** Bottom-right (mobile), top-right (desktop)
**Duration:** 3 seconds (auto-dismiss)

#### Empty States
```jsx
{rooms.length === 0 && (
  <div className="text-center py-12">
    <p className="text-gray-500">No rooms yet</p>
    <button onClick={addRoom}>Add your first room</button>
  </div>
)}
```

#### Error States
```jsx
{error && (
  <div role="alert" className="bg-red-50 p-4 rounded">
    <p className="text-red-800">{error.message}</p>
    <button onClick={retry}>Try again</button>
  </div>
)}
```

### Performance Optimizations

#### Code Splitting
```jsx
// Lazy load pages
const Dashboard = lazy(() => import('./pages/Dashboard'))

<Suspense fallback={<Loading />}>
  <Dashboard />
</Suspense>
```

#### Image Optimization
- Use WebP format with PNG fallback
- Lazy load images below fold
- Responsive images: `srcset`, `sizes`

#### Memoization
```jsx
// Prevent unnecessary re-renders
const MemoizedRoomCard = React.memo(RoomCard)

// Memoize expensive calculations
const sortedRooms = useMemo(() => {
  return rooms.sort((a, b) => a.roomName.localeCompare(b.roomName))
}, [rooms])
```

---

## File Structure

### Complete Project Tree
```
SenseGrid/
├── .github/
│   └── copilot-instructions.md     # AI coding assistant instructions
├── backend/
│   ├── .venv311/                   # Python virtual environment
│   ├── main.py                     # FastAPI app, endpoints, Socket.IO (520 lines)
│   ├── database.py                 # SQLAlchemy models (69 lines)
│   ├── debug_auth.py               # Auth debugging utility
│   ├── verify_install.py           # Dependency verification
│   ├── requirements.txt            # Python dependencies
│   ├── sensegrid.db                # SQLite database (git-ignored)
│   ├── .env                        # Environment variables (git-ignored)
│   └── __pycache__/                # Python bytecode cache
├── frontend/
│   ├── node_modules/               # npm dependencies
│   ├── public/
│   │   ├── icons/
│   │   │   ├── icon-192.png        # PWA icon (192x192)
│   │   │   └── icon-512.png        # PWA icon (512x512)
│   │   ├── manifest.json           # PWA manifest
│   │   └── sw.js                   # Service worker (custom)
│   ├── src/
│   │   ├── components/
│   │   │   ├── RoomCard.jsx        # Room control panel (333 lines)
│   │   │   ├── RoomGrid.jsx        # Room grid layout
│   │   │   ├── RoomGridV2.jsx      # Alternative grid implementation
│   │   │   ├── ActionToggle.jsx    # Toggle switch component
│   │   │   ├── SensorRow.jsx       # Sensor display row
│   │   │   ├── NotificationBell.jsx # Alert notification icon
│   │   │   ├── IntruderModal.jsx   # Intruder alert modal
│   │   │   └── RoomCard.jsx.bak    # Backup file
│   │   ├── hooks/
│   │   │   ├── useAutoActions.js   # Auto-action logic (65 lines)
│   │   │   ├── useOnlineStatus.js  # Network status hook
│   │   │   └── useInstallPrompt.js # PWA install prompt
│   │   ├── mock/
│   │   │   └── rooms.json          # Mock room data for dev
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx       # Main app dashboard
│   │   │   ├── LandingPage.jsx     # Public homepage
│   │   │   ├── LoginPage.jsx       # User login
│   │   │   ├── RegisterPage.jsx    # User registration
│   │   │   └── OnboardingPage.jsx  # First-time setup
│   │   ├── services/
│   │   │   ├── api.js              # Axios HTTP client (114 lines)
│   │   │   ├── offlineQueue.js     # IndexedDB queue (226 lines)
│   │   │   ├── offlineQueueV2.js   # Alternative queue implementation
│   │   │   ├── socket.js           # Socket.IO client (legacy)
│   │   │   └── socket.jsx          # Socket.IO context provider
│   │   ├── store/
│   │   │   └── useStore.js         # Zustand state management
│   │   ├── styles/
│   │   │   └── RoomCard.css        # Custom RoomCard styles
│   │   ├── App.jsx                 # Main app component
│   │   ├── constants.js            # App constants (thresholds, timeouts)
│   │   ├── main.jsx                # React entry point
│   │   └── styles.css              # Global styles (Tailwind imports)
│   ├── .env                        # Frontend env vars (git-ignored)
│   ├── .gitignore                  # Git ignore patterns
│   ├── index.html                  # HTML entry point
│   ├── manifest.webmanifest        # PWA manifest (alternative)
│   ├── package.json                # npm dependencies
│   ├── package-lock.json           # npm lock file
│   ├── postcss.config.cjs          # PostCSS config
│   ├── sw.js                       # Service worker (root)
│   ├── tailwind.config.cjs         # Tailwind CSS config
│   └── vite.config.js              # Vite build config
├── docs/
│   └── raspberry-pi-setup.md       # Hardware setup guide
├── .gitignore                      # Root git ignore
├── OFFLINE_QUEUE.md                # Offline queue API reference
├── PROJECT_DOCUMENTATION.md        # This file
├── README.md                       # Project README
├── RUNNING.md                      # Quick start guide
├── SETUP.md                        # Detailed setup instructions
└── setup.sh                        # Linux/Mac setup script
```

### Key File Descriptions

#### Backend Files
- **`main.py`** - FastAPI application with all endpoints, Socket.IO events, auth utilities
- **`database.py`** - SQLAlchemy ORM models (User, Room, Alert) and session management
- **`requirements.txt`** - Python package dependencies

#### Frontend Core
- **`App.jsx`** - Main app component with router
- **`main.jsx`** - React entry point, renders App with providers
- **`constants.js`** - App-wide constants (thresholds, timeouts)

#### Components
- **`RoomCard.jsx`** - Displays and controls a single room's sensors/actions
- **`RoomGrid.jsx`** - Grid layout wrapper for multiple RoomCards
- **`ActionToggle.jsx`** - Reusable ON/OFF toggle switch
- **`IntruderModal.jsx`** - Modal for intruder alert actions

#### Services
- **`api.js`** - HTTP client with auth interceptors
- **`offlineQueue.js`** - IndexedDB-backed command queue
- **`socket.jsx`** - Socket.IO context provider

#### State
- **`useStore.js`** - Zustand store with auth, rooms state

#### Configuration
- **`vite.config.js`** - Vite build config, PWA plugin setup
- **`tailwind.config.cjs`** - Tailwind CSS customization
- **`package.json`** - npm scripts, dependencies

---

## Troubleshooting

### Common Issues

#### 1. CORS Errors
**Symptom:** Browser console shows "CORS policy blocked"

**Solution:**
```bash
# Backend .env
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://192.168.1.100:5173

# Restart backend after change
```

#### 2. JWT Token Invalid
**Symptom:** 401 errors, auto-redirect to login

**Solution:**
```javascript
// Clear auth state in browser console
localStorage.removeItem('authToken')
localStorage.removeItem('sensegrid-storage')
// Then re-login
```

#### 3. Offline Queue Not Flushing
**Symptom:** Items stuck in queue after going online

**Solution:**
```javascript
// Check queue stats in console
await offlineQueue.getStats()

// Manually flush
await offlineQueue.flushQueue()

// Verify online status
console.log(navigator.onLine)  // Should be true
```

#### 4. Socket.IO Connection Failed
**Symptom:** "WebSocket connection failed" in console

**Solution:**
- Check backend is running: `curl http://localhost:8000/health`
- Verify `VITE_SOCKET_URL` in frontend `.env`
- Check CORS: Socket.IO uses `cors_allowed_origins='*'` in dev
- Test without Socket.IO (app should work offline)

#### 5. Python Module Not Found
**Symptom:** `ModuleNotFoundError` when starting backend

**Solution:**
```bash
# Verify virtual environment is activated
which python  # Should point to .venv311/bin/python

# Reinstall dependencies
pip install -r requirements.txt

# If still failing, recreate venv
rm -rf .venv311
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -r requirements.txt
```

#### 6. Vite Dev Server Won't Start
**Symptom:** Port 5173 in use

**Solution:**
```bash
# Kill process on port 5173
# Linux/Mac:
lsof -ti:5173 | xargs kill -9

# Windows:
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# Or use alternative port
npm run dev -- --port 5174
```

#### 7. Database Schema Mismatch
**Symptom:** SQLAlchemy errors about missing columns

**Solution:**
```bash
# Delete database and recreate (DEV ONLY)
rm backend/sensegrid.db

# Restart backend (tables auto-created)
python -m uvicorn main:app --reload

# For production, use Alembic migrations
alembic upgrade head
```

#### 8. PWA Not Installing
**Symptom:** No install prompt appears

**Solution:**
- Serve over HTTPS or localhost
- Check manifest.json is valid
- Verify service worker registered (DevTools → Application → Service Workers)
- Run Lighthouse audit (PWA score should be 100)

#### 9. Styles Not Loading
**Symptom:** UI looks broken, no styling

**Solution:**
```bash
# Rebuild Tailwind CSS
cd frontend
npm run build

# Clear browser cache
# Chrome: Ctrl+Shift+Delete → Cached images and files

# Verify PostCSS config exists
cat postcss.config.cjs
```

#### 10. High Memory Usage (Backend)
**Symptom:** Backend process consumes excessive RAM

**Solution:**
```python
# Add connection pooling to database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600
)
```

### Debug Commands

#### Frontend Debug Console
```javascript
// Check Zustand store
useStore.getState()

// Check offline queue
await offlineQueue.getStats()
await offlineQueue.list()

// Check Socket.IO status
socket.connected  // true if connected

// Check online status
navigator.onLine  // true if online

// Inspect IndexedDB
// DevTools → Application → Storage → IndexedDB → sensegrid-offline-db
```

#### Backend Debug
```bash
# Test API endpoint
curl http://localhost:8000/health

# Test with auth
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/rooms

# Check database
sqlite3 backend/sensegrid.db "SELECT * FROM users;"

# View logs
python -m uvicorn main:app --reload --log-level debug
```

### Getting Help
1. Check documentation: `README.md`, `SETUP.md`, `OFFLINE_QUEUE.md`
2. Search GitHub issues: https://github.com/ebrahim-77/SenseGrid/issues
3. Create new issue with:
   - Error message
   - Steps to reproduce
   - Browser/OS version
   - Console logs

---

## Further Reading
- **OFFLINE_QUEUE.md** - Complete offline queue API reference and debugging
- **README.md** - Quick start guide and feature overview
- **SETUP.md** - Detailed development environment setup
- **RUNNING.md** - Running the app in different environments
- **docs/raspberry-pi-setup.md** - Hardware integration for IoT devices
- **.github/copilot-instructions.md** - AI coding assistant guidelines

---

## Contributing
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### Coding Standards
- **Frontend:** ESLint + Prettier (`.eslintrc`, `.prettierrc`)
- **Backend:** Black formatter, PEP 8 style guide
- **Commits:** Conventional Commits (e.g., `feat:`, `fix:`, `docs:`)

---

## License
This project is licensed under the MIT License.

---

## Contact & Support
- **GitHub:** https://github.com/ebrahim-77/SenseGrid
- **Issues:** https://github.com/ebrahim-77/SenseGrid/issues
- **Pull Requests:** https://github.com/ebrahim-77/SenseGrid/pulls

For questions or contributions, open an issue or PR on GitHub.

---

**Last Updated:** December 30, 2025  
**Version:** 1.0.0  
**Author:** ebrahim-77
