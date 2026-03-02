# SenseGrid - AI Coding Agent Instructions

## Project Overview
**SenseGrid** is a mobile-first React web application for controlling IoT room sensors with real-time updates and offline-first architecture. The app uses **optimistic UI updates** and **IndexedDB-backed offline queue** to ensure responsive UX even when disconnected.

**Stack**: React 18 + Vite, FastAPI backend, Socket.IO for real-time updates, Zustand for state, Tailwind CSS

## Architecture & Data Flow

### 1. **Offline-First Command Queue** (Critical Pattern)
Commands are sent via an **offline queue** (`frontend/src/services/offlineQueue.js`) that persists to IndexedDB using the `idb` library. This is THE primary integration pattern for device actions.

**Flow**: User action → Optimistic UI update → Try API → On failure, enqueue to IndexedDB → Background sync when online

**Key files**:
- `frontend/src/services/offlineQueue.js` - Queue service with retry logic, event emitter
- `OFFLINE_QUEUE.md` - Queue API reference and console debugging commands

**Usage pattern in components**:
```javascript
// 1. Optimistic update
setRoomState(prev => ({ ...prev, actions: { fan: 'ON' } }))

// 2. Try API call
try {
  await postRoomAction(roomId, command)
  toast.success('Fan set to ON (synced)')
} catch (err) {
  // 3. Enqueue on failure
  await offlineQueue.enqueue({ deviceId, command, ... })
  toast.info('Fan action queued (offline)')
}
```

**Never bypass the queue** - all device commands must go through `postRoomAction()` or `sendDeviceCommand()` → offlineQueue pattern.

### 2. **Real-time Socket.IO Integration**
Socket connection wraps the app via `SocketProvider` context (`frontend/src/services/socket.jsx`). Components use `useSocket()` hook to listen for sensor updates.

**Pattern**: Backend emits `sensorUpdate` → `RoomGrid` listens → Updates Zustand store → UI re-renders

**Key detail**: Socket connection is non-blocking - app works fully offline without socket.io backend.

### 3. **State Management with Zustand**
Global state in `frontend/src/store/useStore.js` persists to localStorage via Zustand middleware.

**State shape**:
```javascript
{
  user: { name, email, ... },
  isAuthenticated: bool,
  rooms: [{ roomId, deviceId, sensors: {}, actions: {}, ... }]
}
```

**Update pattern**: Use `updateRoom(roomId, patch)` to merge changes, not replace entire room object.

### 4. **Optimistic UI Pattern**
All sensor actions show **instant visual feedback** before server confirmation. See `RoomCard.jsx` lines 1-100 for reference implementation.

**Steps**:
1. Update local state immediately
2. Show loading indicator (e.g., "..." on button)
3. API call or enqueue
4. Update final state (success/queued badge)

### 5. **Auto-Actions Logic**
`frontend/src/hooks/useAutoActions.js` evaluates sensor thresholds and triggers fan/alerts automatically **unless manual override is active** (5-minute window).

**Thresholds** (from `constants.js`):
- Temperature > 35°C → Turn fan ON
- Gas > 350 ppm → Turn fan ON
- Humidity > 70% → Turn fan ON

**Manual override**: When user manually toggles, set `room.manualOverrideUntil = Date.now() + MANUAL_OVERRIDE_TIMEOUT` to pause auto-actions.

## Development Workflows

### Starting the Dev Environment
```bash
# Backend (Terminal 1)
cd backend
python -m venv .venv311
source .venv311/bin/activate  # Linux/Mac
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Frontend (Terminal 2)
cd frontend
npm install
npm run dev  # Runs on http://localhost:5174
```

### Testing Offline Queue
1. Open DevTools Console (F12)
2. Go to Network tab → Check "Offline"
3. Toggle any sensor → Should show "Queued" badge
4. Run `await offlineQueue.getStats()` in console
5. Re-enable network → Queue auto-flushes

See `OFFLINE_QUEUE.md` for full debugging commands.

## Code Conventions

### Component Structure
- **Mobile-first**: All layouts start with single-column, scale up with Tailwind breakpoints (`sm:`, `md:`, `lg:`)
- **Touch targets**: Buttons must be ≥44x44px (WCAG 2.1 requirement)
- **Accessibility**: All interactive elements have ARIA labels, keyboard nav support

### API Endpoints
Backend uses **two action endpoints**:
1. `/api/rooms/{roomId}/action` - Preferred for per-sensor toggles
2. `/api/devices/{deviceId}/command` - Fallback for device-wide commands

**Always POST with**:
```javascript
{ command: { sensor, action, value }, homeId, roomId }
```

### File Naming
- Components: PascalCase (e.g., `RoomCard.jsx`)
- Services/Hooks: camelCase (e.g., `offlineQueue.js`, `useAutoActions.js`)
- Pages: PascalCase (e.g., `Dashboard.jsx`)

### Imports
- Use relative imports for project files: `'../services/api'`
- Vite env vars: `import.meta.env.VITE_API_URL`

## Key Files Reference
- `frontend/src/components/RoomCard.jsx` - Full example of optimistic UI + queue pattern
- `frontend/src/services/offlineQueue.js` - Offline queue implementation
- `frontend/src/hooks/useAutoActions.js` - Auto-action threshold logic
- `frontend/src/store/useStore.js` - Zustand state structure
- `backend/main.py` - FastAPI endpoints (minimal stub for development)

## Common Pitfalls
1. **Don't mutate room state directly** - Always use `setRoomState(prev => ({ ...prev, ... }))` or Zustand `updateRoom()`
2. **Don't skip optimistic updates** - Users expect instant feedback even if offline
3. **Don't hardcode thresholds** - Import from `constants.js`
4. **Don't forget ARIA labels** - All buttons need `aria-label` for screen readers
5. **Queue status tracking** - Check `queuedMap` state before showing "Queued" badges

## Testing Checklist
Before committing UI changes, verify:
- ✅ Works in Chrome DevTools mobile emulation (375px width)
- ✅ Offline toggle → Shows queued badge → Syncs when online
- ✅ Keyboard navigation (Tab through all controls)
- ✅ Screen reader announces state changes (NVDA/VoiceOver)
- ✅ No console errors in production build (`npm run build`)

See `README.md` section "🧪 Testing & QA Checklist" for full manual test suite.
