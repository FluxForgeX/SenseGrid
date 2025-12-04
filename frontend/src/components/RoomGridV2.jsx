/**
 * RoomGrid Component - Mobile-first responsive grid layout
 * 
 * Responsive breakpoints:
 * - Mobile (xs): 1 column
 * - Tablet (md): 2 columns
 * - Desktop (lg): 3 columns
 */

import React, { useEffect, useState, useRef } from 'react'
import RoomCard from './RoomCard'
import { fetchRooms, sendDeviceCommand } from '../services/api'
import { useSocket } from '../services/socket'
import evaluateAutoActions from '../hooks/useAutoActions'
import offlineQueue from '../services/offlineQueue'

export default function RoomGrid({ apiBase }) {
  const [rooms, setRooms] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const socket = useSocket()
  const roomsRef = useRef(rooms)
  roomsRef.current = rooms

  useEffect(() => {
    let mounted = true

    async function load() {
      try {
        setLoading(true)
        const data = await fetchRooms()
        
        if (mounted) {
          const enriched = data.map(r => ({
            ...r,
            autoActivated: false,
            pending: false,
            queued: 0,
            queuedItems: [],
            manualOverrideUntil: 0
          }))
          setRooms(enriched)
          setError(null)

          // Evaluate auto actions
          enriched.forEach(r => {
            evaluateAutoActions(r, null, sendDeviceCommand, (roomId, patch) => {
              setRooms(cur => cur.map(x => x.roomId === roomId ? { ...x, ...patch } : x))
            })
          })

          // Load queued items
          updateQueuedState(enriched)
        }
      } catch (e) {
        console.error('Failed to load rooms', e)
        setError('Failed to load rooms')
        
        // Fallback to mock data
        if (mounted) {
          const mocks = getMockRooms()
          setRooms(mocks)
          mocks.forEach(r =>
            evaluateAutoActions(r, null, sendDeviceCommand, (roomId, patch) => {
              setRooms(cur => cur.map(x => x.roomId === roomId ? { ...x, ...patch } : x))
            })
          )
          updateQueuedState(mocks)
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }

    load()

    // Poll queued state every 2 seconds
    const pollInterval = setInterval(() => {
      setRooms(cur => {
        updateQueuedState(cur)
        return cur
      })
    }, 2000)

    return () => {
      mounted = false
      clearInterval(pollInterval)
    }
  }, [apiBase])

  async function updateQueuedState(currentRooms) {
    try {
      const allQueued = await offlineQueue.list()
      const byDevice = {}
      const counts = {}

      allQueued.forEach(q => {
        if (q.status === 'pending') {
          counts[q.deviceId] = (counts[q.deviceId] || 0) + 1
        }
        byDevice[q.deviceId] = byDevice[q.deviceId] || []
        byDevice[q.deviceId].push(q)
      })

      setRooms(cur =>
        cur.map(r => ({
          ...r,
          queued: counts[r.deviceId] || 0,
          queuedItems: byDevice[r.deviceId] || []
        }))
      )
    } catch (e) {
      console.debug('[RoomGrid] queue update failed', e)
    }
  }

  // Handle socket events
  useEffect(() => {
    if (!socket) return

    const handleDeviceUpdate = (payload) => {
      setRooms(prev => {
        const idx = prev.findIndex(r => r.deviceId === payload.deviceId || r.roomId === payload.roomId)
        if (idx === -1) return prev

        const updated = [...prev]
        const room = { ...updated[idx] }
        room.sensors = { ...room.sensors, ...payload.state }
        room.actions = room.actions || {}
        room.lastSeen = payload.ts ?? Date.now()
        updated[idx] = room

        // Evaluate auto actions
        Promise.resolve().then(() =>
          evaluateAutoActions(room, prev[idx], sendDeviceCommand, (roomId, patch) => {
            setRooms(cur => cur.map(r => r.roomId === roomId ? { ...r, ...patch } : r))
          })
        )

        return updated
      })
    }

    const handleSensorUpdate = (payload) => {
      setRooms(prev =>
        prev.map(r => {
          if (r.roomId !== payload.roomId) return r
          const next = {
            ...r,
            sensors: { ...r.sensors, [payload.sensorType]: payload.value },
            lastSeen: payload.ts ?? Date.now()
          }
          Promise.resolve().then(() =>
            evaluateAutoActions(next, r, sendDeviceCommand, (roomId, patch) => {
              setRooms(cur => cur.map(x => x.roomId === roomId ? { ...x, ...patch } : x))
            })
          )
          return next
        })
      )
    }

    const handleActionUpdate = (payload) => {
      setRooms(prev =>
        prev.map(r => {
          if (r.roomId !== payload.roomId) return r
          return {
            ...r,
            actions: { ...(r.actions || {}), [payload.sensorType]: payload.state },
            autoFlags: { ...(r.autoFlags || {}), [payload.sensorType]: !!payload.auto },
            lastSeen: payload.ts ?? Date.now()
          }
        })
      )
    }

    socket.on('device:update', handleDeviceUpdate)
    socket.on('sensor:update', handleSensorUpdate)
    socket.on('action:update', handleActionUpdate)

    return () => {
      socket.off('device:update', handleDeviceUpdate)
      socket.off('sensor:update', handleSensorUpdate)
      socket.off('action:update', handleActionUpdate)
    }
  }, [socket])

  if (loading && rooms.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-4 border-teal-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">Loading rooms...</p>
        </div>
      </div>
    )
  }

  if (error && rooms.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center bg-red-50 p-6 rounded-lg max-w-sm">
          <p className="text-red-600 font-medium mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 auto-rows-max">
      {rooms.map(room => (
        <RoomCard
          key={room.roomId}
          room={room}
          socket={socket}
          queuedItems={room.queuedItems || []}
        />
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
      queued: 0,
      queuedItems: [],
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
      queued: 0,
      queuedItems: [],
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
      queued: 0,
      queuedItems: [],
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
      queued: 0,
      queuedItems: [],
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
      queued: 0,
      queuedItems: [],
      manualOverrideUntil: 0
    },
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
      queued: 0,
      queuedItems: [],
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
      queued: 0,
      queuedItems: [],
      manualOverrideUntil: 0
    }
  ]
}
