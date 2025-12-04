import React, { useEffect, useState, useRef } from 'react'
import RoomCard from './RoomCard'
import { fetchRooms, sendDeviceCommand } from '../services/api'
import { useSocket } from '../services/socket'
import evaluateAutoActions from '../hooks/useAutoActions'
import offlineQueue from '../services/offlineQueue'

export default function RoomGrid({ apiBase }) {
  const [rooms, setRooms] = useState([])
  const socket = useSocket()
  const roomsRef = useRef(rooms)
  roomsRef.current = rooms

  useEffect(() => {
    let mounted = true
    async function load() {
      try {
        const data = await fetchRooms()
        if (mounted) {
          const enriched = data.map(r => ({ ...r, autoActivated: false, pending: false, queued: false, manualOverrideUntil: 0 }))
          setRooms(enriched)
          // evaluate auto actions on initial load
          enriched.forEach(r => {
            // fire-and-forget
            evaluateAutoActions(r, null, sendDeviceCommand, (roomId, patch) => {
              setRooms(cur => cur.map(x => x.roomId === roomId ? { ...x, ...patch } : x))
            })
          })
          // compute initial queued counts and per-device queued items
          try {
            const allQueued = await offlineQueue.list()
            const counts = {}
            const byDevice = {}
            allQueued.forEach(q => {
              counts[q.deviceId] = (counts[q.deviceId] || 0) + 1
              byDevice[q.deviceId] = byDevice[q.deviceId] || []
              byDevice[q.deviceId].push(q)
            })
            setRooms(cur => cur.map(r => ({ ...r, queued: (counts[r.deviceId] || 0), queuedItems: byDevice[r.deviceId] || [] })))
          } catch (e) {
            console.debug('offlineQueue list failed', e)
          }
        }
      } catch (e) {
        console.error('Failed to load rooms', e)
        // fallback mock
        if (mounted) {
          const mocks = getMockRooms()
          setRooms(mocks)
          mocks.forEach(r => evaluateAutoActions(r, null, sendDeviceCommand, (roomId, patch) => {
            setRooms(cur => cur.map(x => x.roomId === roomId ? { ...x, ...patch } : x))
          }))
          // update queued counts and items for mocks
          try {
            const allQueued = await offlineQueue.list()
            const counts = {}
            const byDevice = {}
            allQueued.forEach(q => {
              counts[q.deviceId] = (counts[q.deviceId] || 0) + 1
              byDevice[q.deviceId] = byDevice[q.deviceId] || []
              byDevice[q.deviceId].push(q)
            })
            setRooms(cur => cur.map(r => ({ ...r, queued: (counts[r.deviceId] || 0), queuedItems: byDevice[r.deviceId] || [] })))
          } catch (e) {
            console.debug('offlineQueue list failed for mocks', e)
          }
        }
      }
    }
    load()
    // poll queued counts periodically to keep pending state accurate
    const interval = setInterval(async () => {
      try {
        const allQueued = await offlineQueue.list()
        const counts = {}
        const byDevice = {}
        allQueued.forEach(q => {
          counts[q.deviceId] = (counts[q.deviceId] || 0) + 1
          byDevice[q.deviceId] = byDevice[q.deviceId] || []
          byDevice[q.deviceId].push(q)
        })
        setRooms(cur => cur.map(r => ({ ...r, queued: (counts[r.deviceId] || 0), queuedItems: byDevice[r.deviceId] || [] })))
      } catch (e) {
        // ignore
      }
    }, 3000)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [apiBase])

  // Handle realtime device:update events
  useEffect(() => {
    if (!socket) return
    // device:update handler (legacy): update many sensors at once
    const deviceHandler = async (payload) => {
      // payload: { deviceId, roomId, homeId, state: { temperature, humidity, gas, flame, fanState }, ts }
      setRooms(prev => {
        const idx = prev.findIndex(r => r.deviceId === payload.deviceId || r.roomId === payload.roomId)
        if (idx === -1) return prev
        const updated = [...prev]
        const room = { ...updated[idx] }
        room.sensors = { ...room.sensors, ...payload.state }
        room.actions = room.actions || {}
        room.lastSeen = payload.ts ?? Date.now()
        updated[idx] = room
        // evaluate auto actions after state update
        Promise.resolve().then(() => evaluateAutoActions(room, prev[idx], sendDeviceCommand, (roomId, patch) => {
          setRooms(cur => cur.map(r => r.roomId === roomId ? { ...r, ...patch } : r))
        }))
        return updated
      })
    }

    // sensor:update handler: updates a single sensor value
    const sensorHandler = (payload) => {
      // payload: { roomId, sensorType, value, ts }
      setRooms(prev => prev.map(r => {
        if (r.roomId !== payload.roomId) return r
        const next = { ...r, sensors: { ...r.sensors, [payload.sensorType]: payload.value }, lastSeen: payload.ts ?? Date.now() }
        // evaluate auto actions for this room
        Promise.resolve().then(() => evaluateAutoActions(next, r, sendDeviceCommand, (roomId, patch) => {
          setRooms(cur => cur.map(x => x.roomId === roomId ? { ...x, ...patch } : x))
        }))
        return next
      }))
    }

    // action:update handler: backend tells UI about action state and auto flag
    const actionHandler = (payload) => {
      // payload: { roomId, sensorType, state: 'ON'|'OFF', auto: true|false, ts }
      setRooms(prev => prev.map(r => {
        if (r.roomId !== payload.roomId) return r
        const actions = { ...(r.actions || {}), [payload.sensorType]: payload.state }
        const autoFlags = { ...(r.autoFlags || {}), [payload.sensorType]: !!payload.auto }
        return { ...r, actions, autoFlags, lastSeen: payload.ts ?? Date.now() }
      }))
    }

    socket.on('device:update', deviceHandler)
    socket.on('sensor:update', sensorHandler)
    socket.on('action:update', actionHandler)
    return () => {
      socket.off('device:update', deviceHandler)
      socket.off('sensor:update', sensorHandler)
      socket.off('action:update', actionHandler)
    }
  }, [socket])

  return (
    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
      {rooms.map(room => (
        <RoomCard key={room.roomId} room={room} socket={socket} queuedCount={room.queued || 0} />
      ))}
    </div>
  )
}

function getMockRooms() {
  return [
    {
      roomId: 'r1',
      roomName: 'Living Room',
      homeId: 'h1',
      deviceId: 'd1',
      sensors: { temperature: 24.3, humidity: 45, gas: 200, flame: 0 },
      fanState: 'OFF',
      lastSeen: Date.now(),
      autoActivated: false,
      pending: false,
      queued: false,
      manualOverrideUntil: 0
    },
    {
      roomId: 'r2',
      roomName: 'Kitchen',
      homeId: 'h1',
      deviceId: 'd2',
      sensors: { temperature: 30.1, humidity: 55, gas: 450, flame: 0 },
      fanState: 'OFF',
      lastSeen: Date.now(),
      autoActivated: false,
      pending: false,
      queued: false,
      manualOverrideUntil: 0
    },
    {
      roomId: 'r3',
      roomName: 'Bedroom',
      homeId: 'h1',
      deviceId: 'd3',
      sensors: { temperature: 22.5, humidity: 50, gas: 150, flame: 0 },
      fanState: 'OFF',
      lastSeen: Date.now(),
      autoActivated: false,
      pending: false,
      queued: false,
      manualOverrideUntil: 0
    },
    {
      roomId: 'r4',
      roomName: 'Master Room',
      homeId: 'h1',
      deviceId: 'd4',
      sensors: { temperature: 28.0, humidity: 48, gas: 210, flame: 0 },
      fanState: 'OFF',
      lastSeen: Date.now(),
      autoActivated: false,
      pending: false,
      queued: false,
      manualOverrideUntil: 0
    },
    {
      roomId: 'r5',
      roomName: 'Study Room',
      homeId: 'h1',
      deviceId: 'd5',
      sensors: { temperature: 23.7, humidity: 42, gas: 170, flame: 0 },
      fanState: 'OFF',
      lastSeen: Date.now(),
      autoActivated: false,
      pending: false,
      queued: false,
      manualOverrideUntil: 0
    }
    ,
    {
      roomId: 'r6',
      roomName: 'Garage',
      homeId: 'h1',
      deviceId: 'd6',
      sensors: { temperature: 26.0, humidity: 40, gas: 120, flame: 0 },
      fanState: 'OFF',
      lastSeen: Date.now(),
      autoActivated: false,
      pending: false,
      queued: false,
      manualOverrideUntil: 0
    },
    {
      roomId: 'r7',
      roomName: 'Guest Room',
      homeId: 'h1',
      deviceId: 'd7',
      sensors: { temperature: 25.0, humidity: 48, gas: 160, flame: 0 },
      fanState: 'OFF',
      lastSeen: Date.now(),
      autoActivated: false,
      pending: false,
      queued: false,
      manualOverrideUntil: 0
    },
    
  ]
}


