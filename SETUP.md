# SenseGrid Setup Guide

## Environment Setup

### Backend Configuration

1. **Copy environment template:**
   ```bash
   cd backend
   cp .env.example .env
   ```

2. **Configure `.env` file:**
   ```bash
   # Required: Change JWT_SECRET in production!
   JWT_SECRET=your-super-secret-jwt-key-change-in-production-min-32-chars
   
   # Optional: Adjust if needed
   PORT=8000
   HOST=127.0.0.1
   CORS_ORIGINS=http://localhost:5173,http://localhost:5174
   ```

3. **Install Python dependencies:**
   ```bash
   python -m venv .venv311
   source .venv311/bin/activate  # Linux/Mac
   # or: .venv311\Scripts\Activate.ps1  # Windows PowerShell
   
   pip install -r requirements.txt
   ```

4. **Start backend server:**
   ```bash
   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

   Backend will run on: http://127.0.0.1:8000
   - API docs: http://127.0.0.1:8000/docs
   - Health check: http://127.0.0.1:8000/health

### Frontend Configuration

1. **Copy environment template:**
   ```bash
   cd frontend
   cp .env.example .env
   ```

2. **Configure `.env` file:**
   ```bash
   # API endpoint (should match backend)
   VITE_API_URL=http://localhost:8000/api
   
   # WebSocket endpoint (for Socket.IO)
   VITE_WS_URL=http://localhost:8000
   ```

3. **Install npm dependencies:**
   ```bash
   npm install
   ```

4. **Start dev server:**
   ```bash
   npm run dev
   ```

   Frontend will run on: http://localhost:5174

## Quick Start (Both Servers)

### Terminal 1 - Backend:
```bash
cd backend
source .venv311/bin/activate
python -m uvicorn main:app --reload
```

### Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

## Testing the Setup

1. **Open browser:** http://localhost:5174
2. **Register a new account:**
   - Navigate to "Sign up"
   - Enter name, email, password
   - Should redirect to dashboard
3. **Test offline queue:**
   - Open DevTools (F12) → Network tab
   - Check "Offline" checkbox
   - Toggle any sensor action
   - Should show "Queued" badge
   - Uncheck "Offline"
   - Action should sync automatically

## API Authentication

The backend uses **JWT (JSON Web Tokens)** for authentication:

- **Registration:** `POST /api/auth/register` → Returns token
- **Login:** `POST /api/auth/login` → Returns token
- **Protected routes:** Require `Authorization: Bearer <token>` header

Frontend automatically includes the token via axios interceptor.

## Environment Variables Reference

### Backend (.env)
| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | *(required)* | Secret key for JWT signing (min 32 chars) |
| `PORT` | `8000` | Server port |
| `HOST` | `127.0.0.1` | Server host |
| `CORS_ORIGINS` | `http://localhost:5174` | Allowed CORS origins (comma-separated) |
| `SOCKETIO_ENABLED` | `true` | Enable Socket.IO for real-time updates |

### Frontend (.env)
| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000/api` | Backend API base URL |
| `VITE_WS_URL` | `http://localhost:8000` | WebSocket/Socket.IO URL |
| `VITE_APP_NAME` | `SenseGrid` | Application name |
| `VITE_APP_VERSION` | `1.0.0` | Application version |

## Troubleshooting

### Backend won't start:
```bash
# Check Python version (requires 3.11+)
python --version

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Check port availability
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows
```

### Frontend API errors:
1. Verify backend is running: http://localhost:8000/health
2. Check CORS origins in backend `.env`
3. Clear browser cache and localStorage
4. Check browser console for specific error messages

### Authentication issues:
```bash
# Clear auth state
localStorage.clear()  # In browser console

# Verify JWT_SECRET is set in backend/.env
cat backend/.env | grep JWT_SECRET
```

## Production Deployment

### Security Checklist:
- [ ] Change `JWT_SECRET` to a strong random value (32+ characters)
- [ ] Update `CORS_ORIGINS` to only include production domains
- [ ] Use HTTPS for both frontend and backend
- [ ] Set `HOST=0.0.0.0` only if needed (prefer reverse proxy)
- [ ] Enable rate limiting on auth endpoints
- [ ] Use environment variables, never commit `.env` files

### Database Migration:
Current implementation uses in-memory storage. For production:
1. Add database (PostgreSQL, MongoDB, etc.)
2. Update models in `backend/main.py`
3. Implement database connection
4. Add migration scripts
