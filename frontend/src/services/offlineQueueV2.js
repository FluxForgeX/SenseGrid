/**
 * Offline Queue Service V2
 * Persists commands to IndexedDB using idb library
 * Provides queue management with retry logic and status tracking
 * Exposes hooks for UI to subscribe to queue changes
 */

import { openDB } from 'idb'
import client from './api'

const DB_NAME = 'sensegrid-offline-db'
const STORE_NAME = 'commands'

let dbPromise = null

function getDb() {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, 1, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
          store.createIndex('by-device', 'deviceId')
          store.createIndex('by-status', 'status')
        }
      }
    })
  }
  return dbPromise
}

// Simple event emitter for queue status changes
class QueueEventEmitter {
  constructor() {
    this.listeners = new Map()
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const cbs = this.listeners.get(event)
      const idx = cbs.indexOf(callback)
      if (idx > -1) cbs.splice(idx, 1)
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(cb => cb(data))
    }
  }
}

const emitter = new QueueEventEmitter()

const offlineQueue = {
  // Subscribe to queue changes
  subscribe(event, callback) {
    emitter.on(event, callback)
    return () => emitter.off(event, callback)
  },

  // Enqueue a command
  async enqueue(item) {
    const db = await getDb()
    const commandWithDefaults = {
      ...item,
      id: item.id || `cmd_${Date.now()}_${Math.random().toString(36).slice(2)}`,
      status: 'pending',
      retries: item.retries || 0,
      maxRetries: 5,
      createdAt: item.createdAt || Date.now(),
      lastRetryAt: null
    }
    await db.put(STORE_NAME, commandWithDefaults)
    console.log('[offlineQueue] enqueued', commandWithDefaults.id)
    emitter.emit('enqueued', { item: commandWithDefaults })

    // Auto-flush if online
    if (navigator.onLine) {
      this.flushQueue().catch(e => console.debug('auto-flush on enqueue failed', e))
    }

    return commandWithDefaults.id
  },

  // Get all queued items
  async list() {
    const db = await getDb()
    return await db.getAll(STORE_NAME)
  },

  // Check if a sensor has pending/queued commands
  async isQueuedFor(deviceId, sensor) {
    const db = await getDb()
    const all = await db.getAll(STORE_NAME)
    return all.some(
      item =>
        item.deviceId === deviceId &&
        item.command?.sensor === sensor &&
        item.status !== 'failed'
    )
  },

  // Get queued count for a device
  async getQueuedCountFor(deviceId) {
    const db = await getDb()
    const all = await db.getAll(STORE_NAME)
    return all.filter(item => item.deviceId === deviceId && item.status === 'pending').length
  },

  // Get all queued items for a device
  async getQueuedItemsFor(deviceId) {
    const db = await getDb()
    const all = await db.getAll(STORE_NAME)
    return all.filter(item => item.deviceId === deviceId && item.status === 'pending')
  },

  // Remove a queued item (mark as synced)
  async dequeue(id) {
    const db = await getDb()
    const item = await db.get(STORE_NAME, id)
    if (item) {
      await db.put(STORE_NAME, { ...item, status: 'synced' })
      console.log('[offlineQueue] marked synced', id)
      emitter.emit('synced', { id })
    }
  },

  // Flush the queue (try to POST all pending items)
  async flushQueue() {
    const db = await getDb()
    const items = await db.getAll(STORE_NAME)
    const pending = items.filter(item => item.status === 'pending')

    console.log(`[offlineQueue] flushing ${pending.length} items`)

    for (const item of pending) {
      try {
        // POST to backend
        const endpoint = `/devices/${item.deviceId}/command`
        await client.post(endpoint, {
          command: item.command,
          homeId: item.homeId,
          roomId: item.roomId
        })

        // Mark as synced
        await this.dequeue(item.id)
        console.log('[offlineQueue] synced item', item.id)
        emitter.emit('flushed', { id: item.id })
      } catch (err) {
        const isNetworkError = !err.response
        const statusCode = err.response?.status

        if (isNetworkError) {
          // Network error — don't increment retries, wait for online event
          console.debug('[offlineQueue] network error, aborting flush', err.message)
          return // Stop flush loop
        }

        // Server error — increment retries
        if (item.retries < item.maxRetries) {
          await db.put(STORE_NAME, {
            ...item,
            retries: item.retries + 1,
            lastRetryAt: Date.now()
          })
          console.warn('[offlineQueue] retry #' + (item.retries + 1), item.id, err.message)
        } else {
          // Max retries exceeded — mark as failed
          await db.put(STORE_NAME, { ...item, status: 'failed' })
          console.error('[offlineQueue] item failed after max retries', item.id)
          emitter.emit('failed', { id: item.id, reason: err.message })
        }
      }
    }
  },

  // Clear all queued items
  async clear() {
    const db = await getDb()
    await db.clear(STORE_NAME)
    console.log('[offlineQueue] cleared all items')
  },

  // Get queue stats for debugging
  async getStats() {
    const items = await this.list()
    return {
      total: items.length,
      pending: items.filter(i => i.status === 'pending').length,
      synced: items.filter(i => i.status === 'synced').length,
      failed: items.filter(i => i.status === 'failed').length
    }
  }
}

// Auto-flush when coming back online
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    console.log('[offlineQueue] online detected, flushing queue')
    offlineQueue.flushQueue().catch(e => console.error('[offlineQueue] flush error', e))
  })

  // Register background sync if available
  window.addEventListener('load', async () => {
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      try {
        const reg = await navigator.serviceWorker.ready
        await reg.sync.register('sync-queue')
        console.log('[offlineQueue] background sync registered')
      } catch (e) {
        console.debug('[offlineQueue] background sync unavailable', e)
      }
    }
  })
}

export default offlineQueue
