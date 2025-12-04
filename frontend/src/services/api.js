import axios from 'axios'
import { openDB } from 'idb'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const client = axios.create({ baseURL: API_BASE, timeout: 5000 }) // 5s timeout instead of 10s


// Inject Authorization header from localStorage for each request
client.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem('authToken')
    if (token) config.headers = { ...(config.headers || {}), Authorization: `Bearer ${token}` }
  } catch (e) {
    // ignore
  }
  return config
})

export async function fetchRooms() {
  const res = await client.get('/rooms')
  return res.data
}

export async function sendDeviceCommand(deviceId, command, homeId) {
  const res = await client.post(`/devices/${deviceId}/command`, { command, homeId, roomId: command.roomId })
  return res.data
}

// POST per-room sensor action (preferred endpoint for per-sensor toggles)
export async function postRoomAction(roomId, command, homeId) {
  // Try rooms endpoint first, fallback to devices endpoint if needed
  try {
    const res = await client.post(`/rooms/${roomId}/action`, { command, homeId, roomId })
    return res.data
  } catch (e) {
    // bubble up so caller can attempt device endpoint or enqueue
    throw e
  }
}

export async function sendAlertAction(alertId, action) {
  try {
    return (await client.post(`/frontdoor/${alertId}/${action}`)).data
  } catch (e) {
    return (await client.post(`/alerts/${alertId}/action`, { action })).data
  }
}

// Save auth token into IndexedDB so SW can read it for background sync
export async function saveAuthToIDB(token) {
  try {
    const db = await openDB('sensegrid-db', 1, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('meta')) db.createObjectStore('meta')
      }
    })
    await db.put('meta', token, 'authToken')
  } catch (e) {
    console.warn('saveAuthToIDB failed', e)
  }
}

export default client
