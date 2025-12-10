/**
 * RoomCard Component - Mobile-first responsive room control panel
 * 
 * Features:
 * - Responsive layout: single-column mobile, multi-column desktop
 * - Optimistic UI updates with proper error handling
 * - Offline queue with queue status persistence
 * - Accessibility (ARIA, keyboard nav)
 * - Touch-friendly target sizes (44x44px minimum)
 */

import React, { useState, useEffect, useRef } from 'react'
import { FaTemperatureHigh, FaTint, FaFire, FaWind, FaTrash, FaEdit, FaCheck, FaTimes } from 'react-icons/fa'
import { sendDeviceCommand, postRoomAction } from '../services/api'
import { toast } from 'react-toastify'
import offlineQueue from '../services/offlineQueue'
import { MANUAL_OVERRIDE_TIMEOUT } from '../constants'
import ActionToggle from './ActionToggle'
import '../styles/RoomCard.css'
import { motion } from 'framer-motion'
import useStore from '../store/useStore'

export default function RoomCard({ room, socket, queuedItems = [] }) {
  const removeRoom = useStore(state => state.removeRoom)
  const updateRoom = useStore(state => state.updateRoom)
  const [isEditing, setIsEditing] = useState(false)
  const [editName, setEditName] = useState(room.roomName || '')

  // Local optimistic state
  const [roomState, setRoomState] = useState(room || {})
  const roomRef = useRef(room)
  const roomStateRef = useRef(roomState)
  
  // Track queued sensors from offlineQueue
  const [queuedMap, setQueuedMap] = useState({})

  // Keep refs in sync
  useEffect(() => {
    roomRef.current = room
  }, [room])

  useEffect(() => {
    roomStateRef.current = roomState
  }, [roomState])

  // Merge incoming room prop (preserve optimistic fields)
  useEffect(() => {
    setRoomState(prev => {
      if (!prev) return { ...(room || {}) }
      return {
        ...prev,
        ...(room || {}),
        actions: { ...(prev.actions || {}), ...((room && room.actions) || {}) },
        autoFlags: { ...(prev.autoFlags || {}), ...((room && room.autoFlags) || {}) }
      }
    })
  }, [room])

  // Build queued map from queuedItems prop OR from offlineQueue
  useEffect(() => {
    const qm = {}
    
    // Check server-provided queued items
    if (room?.queuedItems && Array.isArray(room.queuedItems)) {
      room.queuedItems.forEach(i => {
        const sensor = i?.command?.sensor
        if (sensor) qm[sensor] = true
      })
    }

    // Also check local offlineQueue for this device
    offlineQueue.getQueuedItemsFor(room?.deviceId).then(items => {
      items.forEach(item => {
        const sensor = item?.command?.sensor
        if (sensor) qm[sensor] = true
      })
      setQueuedMap(qm)
    }).catch(() => {
      setQueuedMap(qm)
    })
  }, [room?.queuedItems, room?.deviceId])

  // Subscribe to queue changes
  useEffect(() => {
    const unsubFlushed = offlineQueue.subscribe('flushed', ({ id }) => {
      // Clear queued state for synced items
      offlineQueue.getQueuedItemsFor(room?.deviceId).then(items => {
        const qm = {}
        items.forEach(item => {
          const sensor = item?.command?.sensor
          if (sensor && item.status === 'pending') qm[sensor] = true
        })
        setQueuedMap(qm)
      })
    })

    return () => {
      unsubFlushed()
    }
  }, [room?.deviceId])

  function sensorsLabel(key) {
    return ({ temperature: 'Temperature', humidity: 'Humidity', gas: 'Gas', flame: 'Flame' }[key] || key)
  }

  const sensors = [
    { key: 'temperature', label: 'Temperature', icon: <FaTemperatureHigh />, value: roomState.sensors?.temperature, unit: '°C' },
    { key: 'humidity', label: 'Humidity', icon: <FaTint />, value: roomState.sensors?.humidity, unit: '%' },
    { key: 'gas', label: 'Gas', icon: <FaWind />, value: roomState.sensors?.gas, unit: '' },
    { key: 'flame', label: 'Flame', icon: <FaFire />, value: roomState.sensors?.flame, unit: '' }
  ]

  /**
   * Handle toggle - optimistic update + network attempt + offline queue fallback
   */
  async function handleToggle(sensor, value) {
    const stableRoom = roomRef.current || {}
    const { roomId, deviceId, homeId } = stableRoom

    const cmdId = `cmd_${Date.now()}_${Math.random().toString(36).slice(2)}`
    const command = { action: 'set', sensor, value, id: cmdId }

    // Record previous for revert
    const prevValue = roomStateRef.current?.actions?.[sensor] ?? 'OFF'

    // Optimistic UI
    setRoomState(prev => ({
      ...prev,
      actions: { ...(prev.actions || {}), [sensor]: value },
      manualOverrideUntil: Date.now() + MANUAL_OVERRIDE_TIMEOUT
    }))

    // Immediately resolve for ActionToggle
    const result = Promise.resolve(true)

    // Background work
    ;(async () => {
      try {
        if (navigator.onLine) {
          try {
            // Try rooms endpoint first
            await postRoomAction(roomId, command, homeId)
            console.debug('[RoomCard] postRoomAction succeeded')
          } catch (err) {
            // Fallback to device endpoint
            await sendDeviceCommand(deviceId, { action: 'set', target: sensor, value, id: cmdId, roomId }, homeId)
            console.debug('[RoomCard] sendDeviceCommand succeeded')
          }

          // Clear queued state
          setQueuedMap(prev => ({ ...prev, [sensor]: false }))
          toast.success(`${sensorsLabel(sensor)} set to ${value} (synced)`)
        } else {
          // Offline - enqueue
          await offlineQueue.enqueue({
            id: cmdId,
            deviceId,
            command,
            homeId,
            roomId,
            createdAt: Date.now(),
            retries: 0
          })
          setQueuedMap(prev => ({ ...prev, [sensor]: true }))
          toast.info(`${sensorsLabel(sensor)} action queued (offline)`)
        }
      } catch (err) {
        console.error('[RoomCard] action failed', err)

        // Revert optimistic UI if still showing our value
        setRoomState(prev => {
          const current = prev.actions?.[sensor]
          if (current === value) {
            return {
              ...prev,
              actions: { ...(prev.actions || {}), [sensor]: prevValue }
            }
          }
          return prev
        })

        // Try enqueue as fallback
        try {
          await offlineQueue.enqueue({
            id: cmdId,
            deviceId,
            command,
            homeId,
            roomId,
            createdAt: Date.now(),
            retries: 0
          })
          setQueuedMap(prev => ({ ...prev, [sensor]: true }))
          toast.info(`${sensorsLabel(sensor)} action queued after error`)
        } catch (qerr) {
          console.error('[RoomCard] failed to enqueue', qerr)
          toast.error(`${sensorsLabel(sensor)} action failed`)
        }
      }
    })()

    return result
  }

  const handleSave = () => {
    if (editName.trim()) {
      updateRoom(room.roomId, { roomName: editName })
      setIsEditing(false)
    }
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -5 }}
      className="bg-white rounded-lg shadow-md p-4 sm:p-6 transition-all duration-200 relative group"
    >
      <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition z-10">
        <button 
          onClick={() => {
            setEditName(roomState.roomName)
            setIsEditing(true)
          }}
          className="text-gray-400 hover:text-teal-500"
          title="Edit Room"
        >
          <FaEdit />
        </button>
        <button 
          onClick={() => removeRoom(room.roomId)}
          className="text-gray-400 hover:text-red-500"
          title="Remove Room"
        >
          <FaTrash />
        </button>
      </div>

      {/* Room header */}
      <div className="mb-4 sm:mb-6 pr-16">
        {isEditing ? (
          <div className="flex items-center gap-2">
            <input 
              type="text" 
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1 text-sm w-full focus:outline-none focus:border-teal-500"
              autoFocus
            />
            <button onClick={handleSave} className="text-green-500 hover:text-green-600"><FaCheck /></button>
            <button onClick={() => setIsEditing(false)} className="text-red-500 hover:text-red-600"><FaTimes /></button>
          </div>
        ) : (
          <h2 className="text-lg sm:text-xl font-semibold text-gray-900 truncate">
            {roomState.roomName || 'Room'}
          </h2>
        )}
        <p className="text-xs sm:text-sm text-gray-500 mt-1">
          Last seen: {roomState.lastSeen ? new Date(roomState.lastSeen).toLocaleTimeString() : 'never'}
        </p>
      </div>

      {/* Sensors grid - responsive */}
      <div className="space-y-4 sm:space-y-6">
        {sensors.map(s => (
          <div key={s.key} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 pb-4 sm:pb-0 border-b sm:border-b-0 last:border-b-0">
            {/* Sensor info */}
            <div className="flex items-start gap-3 sm:gap-4 flex-1 min-w-0">
              <div className="text-teal-500 flex-shrink-0 mt-0.5">
                {s.icon}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm sm:text-base font-medium text-gray-900 truncate">
                  {s.label}
                </h3>
                <p className="text-xs sm:text-sm text-gray-600 mt-0.5">
                  {s.value !== null && s.value !== undefined ? `${s.value}${s.unit ? ` ${s.unit}` : ''}` : '—'}
                </p>
              </div>
            </div>

            {/* Action button - responsive */}
            <div className="flex-shrink-0 w-full sm:w-auto">
              <ActionToggle
                roomId={roomRef.current?.roomId}
                sensor={s.key}
                state={roomState.actions?.[s.key] || 'OFF'}
                auto={roomState.autoFlags?.[s.key]}
                queued={!!queuedMap[s.key]}
                onToggle={(sensor, newValue) => handleToggle(sensor, newValue)}
              />
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
