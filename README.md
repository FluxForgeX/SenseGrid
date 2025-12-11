# SenseGrid - Progressive Web App IoT Dashboard

A mobile-first, responsive React PWA for controlling IoT room sensors with real-time socket updates, offline support, and background sync.

## 🚀 Quick Start (Localhost / Raspberry Pi)

```bash
# Clone and run setup
git clone <your-repo-url>
cd SenseGrid
chmod +x setup.sh && ./setup.sh

# OR manual setup:

# Backend (Terminal 1)
cd backend
python -m venv .venv311
source .venv311/bin/activate  # Linux/Mac/Pi
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend (Terminal 2)
cd frontend
npm install
npm run dev
```

📖 **For Raspberry Pi deployment**, see [docs/raspberry-pi-setup.md](docs/raspberry-pi-setup.md)

## 🚀 Features

- ✅ **Mobile-First Responsive** — Optimized for phones, tablets, and desktops
- ✅ **Progressive Web App** — Installable, works offline, background sync
- ✅ **Real-time Updates** — Socket.IO integration for live sensor data
- ✅ **Offline Queue** — Commands persist to IndexedDB, sync when online
- ✅ **Touch-Friendly** — 44x44px minimum touch targets (WCAG compliant)
- ✅ **Accessible** — ARIA labels, keyboard navigation, proper contrast
- ✅ **Optimistic UI** — Instant visual feedback for user actions
- ✅ **SQLite Database** — Persistent storage for users, rooms, and alerts

## 📋 Installation

### Prerequisites
- Node.js 16+ and npm
- Python 3.11+ (for backend)

### Frontend Setup

```bash
cd frontend
npm install
npm run dev          # Start dev server (http://localhost:5173)
npm run build        # Build for production
npm run preview      # Preview production build
```

### Backend Setup

```bash
cd backend
python -m venv .venv311
source .venv311/bin/activate  # Linux/Mac
# or: .venv311\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

Create `.env` in `backend/`:
```env
JWT_SECRET=your-super-secret-key-min-32-chars
CORS_ORIGINS=http://localhost:5173,http://192.168.1.100:5173
```

Create `.env` in `frontend/`:
```env
VITE_API_URL=http://localhost:8000
VITE_SOCKET_URL=http://localhost:8000
```

## 🧪 Testing & QA Checklist

### 1. Online Toggle (Happy Path)
```
✓ Open http://localhost:5173 in browser
✓ Open DevTools Console (F12)
✓ Click "ON/OFF" button on any sensor
✓ Expect: Button instantly toggles → "... " loading state → final state
✓ Toast shows "Temperature set to ON (synced)"
✓ Console shows: [RoomCard] postRoomAction succeeded
✓ Backend logs show: [backend] received room action...
```

### 2. Offline Toggle (Queue Path)
```
✓ DevTools Network → Offline checkbox, OR unplug network
✓ Click a toggle button
✓ Expect:
   - Button toggles optimistically (instant visual feedback)
   - Gray "Queued" badge appears next to button
   - Toast shows "Temperature action queued (offline)"
   - Console: [offlineQueue] enqueued cmd_...
✓ Reload page → item still queued (IndexedDB persistent)
✓ Re-enable network
✓ Expect:
   - Queued badge disappears after ~2 seconds
   - Console: [offlineQueue] synced item cmd_...
   - Toast shows "Temperature set to ON (synced)"
```

### 3. Mobile Layout
```
✓ DevTools → Device Emulation → iPhone SE (375px)
✓ Room cards display as single column
✓ Sensor info stacks: [Icon] [Label] [Value]
✓ Action button directly below, full width
✓ Button is at least 44x44px (touch-friendly)
✓ No text overflow, readable font sizes
✓ Pinch-to-zoom works (viewport meta tag respected)
```

### 4. Responsive Grid
```
✓ Mobile (≤640px): 1 column
✓ Tablet (641px-1024px): 2 columns
✓ Desktop (>1024px): 3 columns
✓ Gaps and padding increase on larger screens
✓ No layout shifts when resizing
```

### 5. Accessibility
```
✓ Tab through all buttons (keyboard nav works)
✓ Focus visible (blue outline appears)
✓ Screen reader announces toggle state:
   "Temperature: ON. Auto mode enabled. Queued for sync."
✓ Enter or Space key toggles button
✓ Color contrast: buttons pass WCAG AA standard
✓ Toast notifications are readable
```

### 6. PWA Installation
```
✓ Open app in Chrome/Edge on desktop/mobile
✓ Address bar shows "+" install icon (or app menu option)
✓ Click install → opens install dialog
✓ Confirm → app installs
✓ Launch from home screen
✓ Works in standalone mode (no browser URL bar)
✓ Service worker offline.html fallback works
```

### 7. Service Worker & Background Sync
```
✓ DevTools → Application → Service Workers → registered
✓ Offline mode: click toggle → queued ✓
✓ Device goes online (or DevTools → offline toggle off)
✓ Without manual action, queued items flush within 2 seconds
✓ Backend receives POST requests
✓ UI updates to show synced state
```

### 8. Queue Persistence
```
✓ Browser DevTools → Storage → IndexedDB → sensegrid-offline-db → commands
✓ Items have: id, deviceId, command, status ('pending'|'synced'|'failed'), retries
✓ After page reload, queued items still exist
✓ Manual queue clear: open Console, run: offlineQueue.clear()
✓ Queue stats: await offlineQueue.getStats() → { total, pending, synced, failed }
```

### 9. Error Handling
```
✓ Stop backend server
✓ Click toggle → button toggles, queued badge appears
✓ Console shows: [offlineQueue] network error
✓ Item is queued (not marked failed prematurely)
✓ Retry count does not increment (waits for online event)
✓ Start backend again
✓ Queue flushes automatically within 2 seconds
```

### 10. Auto Actions (if implemented)
```
✓ Room reaches threshold (e.g., temperature > 30°C)
✓ Auto action triggers without user clicking
✓ "Auto" badge shown on affected sensor
✓ Manual override: click toggle → manual state lasts 30 min
✓ After 30 min, auto mode resumes
```

## 📊 Architecture

### Frontend Stack
- **Framework**: React 18 + Vite
- **Styling**: Tailwind CSS (mobile-first)
- **Real-time**: Socket.IO client
- **Offline**: IndexedDB (idb library)
- **HTTP**: axios with request interceptors
- **UI**: react-toastify, react-icons

### Backend Stack
- **Framework**: FastAPI + uvicorn
- **API**: RESTful endpoints for commands
- **WebSocket**: Socket.IO for real-time (optional)
- **Database**: In-memory (mock) for dev, can extend

### Offline Flow
```
User click toggle
  ↓
Optimistic UI update
  ↓
Try POST to /api/rooms/:id/action or /api/devices/:id/command
  │
  ├─ Success → clear queued, show synced toast
  │
  └─ Fail → enqueue to IndexedDB
       ↓
       Register background sync (if supported)
       Poll queue on online event
       POST each item
       Mark synced when successful
```

## 🛠️ Key Files

| File | Purpose |
|------|---------|
| `src/components/RoomGrid.jsx` | Responsive grid (1/2/3 cols) + socket handlers |
| `src/components/RoomCard.jsx` | Card layout + action toggle logic |
| `src/components/ActionToggle.jsx` | Button with queued/error/loading states + a11y |
| `src/services/offlineQueue.js` | IndexedDB queue, flush, event emitter |
| `src/services/api.js` | axios client + interceptors |
| `src/services/socket.jsx` | Socket.IO provider (gracefully fails if unavailable) |
| `src/styles/RoomCard.css` | Mobile-first responsive styles |
| `src/styles.css` | Tailwind + global styles + safe area padding |
| `tailwind.config.cjs` | Breakpoints, colors, touch target sizes |
| `vite.config.js` | Vite + PWA plugin config + workbox caching |
| `public/manifest.webmanifest` | PWA manifest (name, icons, scope) |
| `backend/main.py` | FastAPI endpoints (rooms, device commands) |

## 🔧 Queue Management (Console Commands)

```javascript
// Check queue stats
await offlineQueue.getStats()
// Output: { total: 3, pending: 2, synced: 1, failed: 0 }

// Get queued items for a device
await offlineQueue.getQueuedItemsFor('d1')

// Check if a sensor has queued commands
await offlineQueue.isQueuedFor('d1', 'temperature')
// Output: true or false

// Manually flush queue
await offlineQueue.flushQueue()

// Clear all queued items
await offlineQueue.clear()

// Subscribe to queue changes
const unsub = offlineQueue.subscribe('flushed', ({ id }) => {
  console.log('Item synced:', id)
})
```

## 📱 Responsive Breakpoints

```css
xs: 320px   /* Extra small phones */
sm: 640px   /* Small phones + large phones */
md: 768px   /* Tablets */
lg: 1024px  /* Small laptops */
xl: 1280px  /* Desktop */
```

Use Tailwind utilities:
```jsx
<div className="text-sm md:text-base lg:text-lg">
  Responsive text size
</div>
```

## 🌐 Environment Variables

Create `.env` in `frontend/` if needed:
```
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=http://localhost:8000
```

These are optional; defaults work for local development.

## 📦 Service Worker & PWA Config

- **Plugin**: `vite-plugin-pwa` (configured in `vite.config.js`)
- **Strategy**:
  - Shell assets (JS, CSS, HTML): CacheFirst
  - API calls: NetworkFirst with fallback
  - Icons: CacheFirst
- **Icons**: Place `icon-192.png` and `icon-512.png` in `public/icons/`
- **Manifest**: `public/manifest.webmanifest` (auto-generated, can customize)

To regenerate:
```bash
npm run build
# Check dist/manifest.webmanifest and dist/service-worker.js
```

## 🎨 Tailwind Tips

- Mobile-first: write base styles, then add responsive overrides
- Touch targets: use `min-h-touch` / `min-w-touch` (44x44px)
- Safe area: padding respects notches on iOS with `padding-safe`
- Colors: Use semantic names like `bg-teal-500`, `text-gray-900`

Example:
```jsx
<button className="min-h-touch min-w-touch px-4 py-2 bg-teal-500 hover:bg-teal-600 text-white rounded">
  Click me
</button>
```

## 🔍 Debugging

### Console Logs
- `[RoomCard]` - room-level action logs
- `[ActionToggle]` - button click and state logs
- `[offlineQueue]` - queue enqueue, flush, sync logs
- `[socket]` - socket connection attempts (debug level)

### DevTools
1. **Network**: Monitor API calls and service worker requests
2. **Application**:
   - **Service Workers**: Check registration status
   - **IndexedDB**: View `sensegrid-offline-db` → `commands` store
   - **Cache**: View cached assets
   - **Manifest**: Verify PWA manifest loads

### Test Commands
```bash
# Check manifest valid
curl http://localhost:5174/manifest.webmanifest | jq

# Test API endpoint
curl -X POST http://localhost:8000/api/devices/d1/command \
  -H "Content-Type: application/json" \
  -d '{"command":{"sensor":"temperature","value":"ON"}}'
```

## 📚 Additional Resources

- [Tailwind CSS Docs](https://tailwindcss.com)
- [React Docs](https://react.dev)
- [Socket.IO Docs](https://socket.io/docs/)
- [IndexedDB MDN](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API)
- [PWA Docs](https://web.dev/progressive-web-apps/)
- [WCAG Accessibility](https://www.w3.org/WAI/WCAG21/quickref/)

## 📝 License

MIT (or your license here)

## 🤝 Contributing

Contributions welcome! Please:
1. Test on mobile and desktop
2. Check accessibility (keyboard + screen reader)
3. Verify offline queue persists and syncs
4. Follow existing code style
