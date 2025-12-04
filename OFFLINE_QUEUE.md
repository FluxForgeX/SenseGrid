# Offline Queue Management Guide

## Quick Reference

The **offline queue** stores commands in **IndexedDB** when the network is unavailable. Commands are automatically flushed when the device comes back online.

## Queue States

Each command in the queue has a status:

- **`pending`** — Waiting to be sent to the server
- **`synced`** — Successfully sent and acknowledged
- **`failed`** — Failed after max retries (5 attempts)

## Console Commands

Open DevTools Console (F12) and use these commands:

### View Queue Stats
```javascript
await offlineQueue.getStats()
```
Returns:
```javascript
{
  total: 5,
  pending: 2,
  synced: 3,
  failed: 0
}
```

### View All Queued Items
```javascript
const items = await offlineQueue.list()
console.table(items)
```

Output:
```
id            deviceId command                     status   retries createdAt
cmd_123       d1       {sensor: "temperature", ...} pending  0      1701612345000
cmd_124       d2       {sensor: "humidity", ...}    pending  1      1701612400000
cmd_125       d1       {sensor: "gas", ...}         synced   0      1701612350000
```

### Check if Sensor is Queued
```javascript
// Does device d1, sensor "temperature" have pending commands?
const isQueued = await offlineQueue.isQueuedFor('d1', 'temperature')
console.log(isQueued) // true or false
```

### Get Queued Items for a Device
```javascript
const items = await offlineQueue.getQueuedItemsFor('d1')
console.log(`Device d1 has ${items.length} queued items`)
```

### Manually Flush Queue
```javascript
// Try to send all pending items to backend
await offlineQueue.flushQueue()
```

Console output:
```
[offlineQueue] flushing 2 items
[offlineQueue] synced item cmd_123
[offlineQueue] synced item cmd_124
```

### Clear All Queue Data
```javascript
// ⚠️ WARNING: This deletes ALL queued items permanently!
await offlineQueue.clear()
```

## Queue Events (Subscribe)

You can listen to queue changes in your code:

```javascript
// Listen for item synced
const unsub = offlineQueue.subscribe('flushed', ({ id }) => {
  console.log(`Item ${id} was synced!`)
  // UI can update here
})

// Listen for enqueue
offlineQueue.subscribe('enqueued', ({ item }) => {
  console.log(`New item enqueued:`, item)
})

// Listen for failure (after max retries)
offlineQueue.subscribe('failed', ({ id, reason }) => {
  console.log(`Item ${id} failed: ${reason}`)
})

// Unsubscribe when done
unsub()
```

## Retry Logic

- Each item can be retried up to **5 times** before being marked `failed`
- Retries only happen on **server errors** (5xx, 4xx)
- **Network errors** (no connection) do NOT increment retry count — the item waits for the online event
- Each retry adds `1` to the `retries` counter
- `lastRetryAt` timestamp is updated on each attempt

## Storage Location

Queue data is stored in **IndexedDB**:

- **Database**: `sensegrid-offline-db`
- **Store**: `commands`
- **Indexes**: `by-device`, `by-status`

To view in DevTools:
1. Open DevTools (F12)
2. Go to **Application** tab
3. Expand **IndexedDB** → `sensegrid-offline-db` → `commands`
4. Browse items

## Auto-Flush Triggers

The queue is automatically flushed in these scenarios:

1. **User comes online** — `window.addEventListener('online', ...)`
2. **Item enqueued while online** — Try immediate flush
3. **Background Sync** — Service worker syncs after device wakes (if supported)
4. **Socket reconnect** — When socket.io reconnects (handled by RoomGrid)

## Example: Queue an Item Manually

```javascript
// Enqueue a temperature command for device d1
await offlineQueue.enqueue({
  id: `cmd_${Date.now()}`,
  deviceId: 'd1',
  command: {
    action: 'set',
    sensor: 'temperature',
    value: 'ON'
  },
  homeId: 'h1',
  roomId: 'r1',
  retries: 0
})
```

## Troubleshooting

### Queue items not flushing?
1. Check backend is running: `curl http://localhost:8000/health`
2. Check network is online: `console.log(navigator.onLine)`
3. Manually flush: `await offlineQueue.flushQueue()`
4. Check browser console for errors

### Items marked as failed?
1. Check backend logs for errors
2. Fix the issue (e.g., add missing field to command)
3. Edit item in IndexedDB or clear and re-enqueue
4. Call `await offlineQueue.flushQueue()` again

### IndexedDB taking too much storage?
1. View size in DevTools: Application → Storage → Usage
2. Clear old synced items: `await offlineQueue.clear()`
3. Use Firefox/DevTools to inspect storage quotas

## Integration with UI

The `RoomCard` component automatically:
- Enqueues failed commands
- Updates `queuedMap` state from offlineQueue
- Clears queued badge when item syncs
- Shows toast notifications

The `RoomGrid` component:
- Polls offlineQueue every 2 seconds
- Updates UI with queued counts

## API Reference

```typescript
interface OfflineQueueService {
  // Enqueue a command
  enqueue(item: {
    id?: string
    deviceId: string
    command: any
    homeId?: string
    roomId?: string
    retries?: number
    createdAt?: number
  }): Promise<string> // returns command id

  // Get all items
  list(): Promise<Array>

  // Check if sensor is queued
  isQueuedFor(deviceId: string, sensor: string): Promise<boolean>

  // Get queued count for device
  getQueuedCountFor(deviceId: string): Promise<number>

  // Get queued items for device
  getQueuedItemsFor(deviceId: string): Promise<Array>

  // Mark item as synced
  dequeue(id: string): Promise<void>

  // Flush all pending items
  flushQueue(): Promise<void>

  // Get stats
  getStats(): Promise<{
    total: number
    pending: number
    synced: number
    failed: number
  }>

  // Clear all items
  clear(): Promise<void>

  // Subscribe to events
  subscribe(event: 'enqueued'|'flushed'|'failed', callback: Function): () => void
}
```

## Performance Notes

- IndexedDB queries are fast (<1ms for 100 items)
- Polling every 2 seconds is safe (not a performance issue)
- Large payloads (>1MB) may impact storage quota
- Synced items stay in IndexedDB for audit trail (clean up periodically with `.clear()`)
