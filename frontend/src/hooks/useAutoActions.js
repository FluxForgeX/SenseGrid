import { TEMPERATURE_LIMIT, GAS_LIMIT, HUMIDITY_LIMIT, MANUAL_OVERRIDE_TIMEOUT } from '../constants'
import offlineQueue from '../services/offlineQueue'

// Evaluate auto-action conditions for a room based on new sensor values.
// If conditions are met and no recent manual override exists, send a command to turn the fan ON.
// updateRoom is a callback: (roomId, patch) => void to update room state in the parent.
export async function evaluateAutoActions(room, prevRoom, sendDeviceCommand, updateRoom) {
  // don't act if no room or no send function
  if (!room || !sendDeviceCommand) return

  const now = Date.now()
  const manualUntil = room.manualOverrideUntil || 0
  const manualActive = now < manualUntil

  // helper to create and send/queue command
  async function triggerAuto(reason) {
    // if fan already ON, nothing to do
    if (room.fanState === 'ON') {
      updateRoom(room.roomId, { autoActivated: true })
      return
    }

    const cmdId = 'cmd_' + (crypto && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2))
    const command = {
      action: 'set',
      target: 'fan',
      value: 'ON',
      reason: 'auto:' + reason,
      id: cmdId
    }

    // optimistic update: reflect fan ON and autoActivated
    updateRoom(room.roomId, { fanState: 'ON', autoActivated: true, pending: true })

    try {
      await sendDeviceCommand(room.deviceId, command, room.homeId)
      // succeeded
      updateRoom(room.roomId, { pending: false, queued: false })
    } catch (err) {
      // queue for background sync
      await offlineQueue.enqueue({ id: cmdId, deviceId: room.deviceId, command, homeId: room.homeId, createdAt: Date.now(), retries: 0 })
      updateRoom(room.roomId, { pending: false, queued: true })
    }
  }

  if (manualActive) {
    // Respect manual override window — do not auto-trigger
    return
  }

  // Temperature
  if (typeof room.sensors?.temperature === 'number' && room.sensors.temperature > TEMPERATURE_LIMIT) {
    await triggerAuto('temperature')
    return
  }

  // Gas
  if (typeof room.sensors?.gas === 'number' && room.sensors.gas > GAS_LIMIT) {
    await triggerAuto('gas')
    return
  }

  // Flame
  if (typeof room.sensors?.flame === 'number' && room.sensors.flame === 1) {
    await triggerAuto('flame')
    return
  }

  // Humidity optional
  if (typeof room.sensors?.humidity === 'number' && room.sensors.humidity > HUMIDITY_LIMIT) {
    await triggerAuto('humidity')
    return
  }
}

export default evaluateAutoActions
