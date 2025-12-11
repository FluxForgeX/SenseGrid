# 🚀 SenseGrid - Backend & Frontend Connected

## ✅ Successfully Running

### Backend Server
- **URL**: http://127.0.0.1:8000
- **API Docs**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/health
- **Status**: ✅ Running with JWT authentication

### Frontend Server  
- **URL**: http://localhost:5173
- **Status**: ✅ Running with Vite dev server

## 🔐 Authentication Features

### Implemented Endpoints:
- `POST /api/auth/register` - Create new account
- `POST /api/auth/login` - Login with credentials
- `GET /api/auth/me` - Get current user (requires auth)
- `GET /api/rooms` - List user's rooms (requires auth)
- `POST /api/rooms` - Create new room (requires auth)
- `POST /api/rooms/{roomId}/action` - Control room devices (requires auth)
- `POST /api/devices/{deviceId}/command` - Send device commands (requires auth)

## 🧪 Quick Test

### 1. Register a new user:
```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"password123"}'
```

### 2. Login:
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### 3. Get rooms (with token):
```bash
TOKEN="your_token_here"
curl http://127.0.0.1:8000/api/rooms \
  -H "Authorization: Bearer $TOKEN"
```

## 📱 Frontend Testing

1. Open: http://localhost:5173
2. Click "Sign up" or "Log in"
3. Create an account with any email/password
4. You'll be redirected to the dashboard
5. A default "Living Room" will be created
6. Try toggling sensors (they'll work with real backend now!)

## 🔄 Real-time Features

- **Offline Queue**: Works with real backend - actions queue when offline
- **Socket.IO**: Backend has Socket.IO support for real-time sensor updates
- **Optimistic UI**: Instant feedback before server confirms

## 🛠️ Development Commands

### Stop servers:
```bash
# Kill backend
pkill -f uvicorn

# Frontend (Ctrl+C in terminal)
```

### Restart:
```bash
# Backend
cd backend && python -m uvicorn main:app --reload

# Frontend  
cd frontend && npm run dev
```

## 📝 Environment Files

Both `.env` files are created and configured:
- `backend/.env` - Backend configuration with JWT secret
- `frontend/.env` - Frontend API endpoints

## 🎯 Next Steps

1. Open http://localhost:5173 in your browser
2. Register a new account
3. Test sensor controls with real backend
4. Try offline mode (DevTools → Network → Offline)
5. See actions queue and sync when back online!

---

**Backend Process ID**: Check with `ps aux | grep uvicorn`
**Frontend**: Running in Vite dev server with hot reload
