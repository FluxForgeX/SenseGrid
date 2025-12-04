/* Simple service worker to flush queued commands from IndexedDB on sync event.
   This is a minimal implementation: it opens the same DB 'sensegrid-db' and reads the 'commands' store.
   For each queued command it attempts to POST to `/api/devices/{deviceId}/command` with body { command, homeId }.
   On success the entry is removed.
*/

self.addEventListener('install', (e) => {
  self.skipWaiting()
})

self.addEventListener('activate', (e) => {
  e.waitUntil(self.clients.claim())
})

function openIDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('sensegrid-db', 1)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains('commands')) db.createObjectStore('commands', { keyPath: 'id' })
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function getAllCommands(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('commands', 'readonly')
    const store = tx.objectStore('commands')
    const req = store.getAll()
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function deleteCommand(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('commands', 'readwrite')
    const store = tx.objectStore('commands')
    const req = store.delete(id)
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-commands') {
    event.waitUntil((async () => {
      try {
        const db = await openIDB()
        const cmds = await getAllCommands(db)
        for (const item of cmds) {
          try {
            const url = `/api/devices/${item.deviceId}/command`
            const res = await fetch(url, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ command: item.command, homeId: item.homeId })
            })
            if (res.ok) {
              await deleteCommand(db, item.id)
            }
          } catch (e) {
            // If any command fails, leave it in DB and continue — sync will retry later
            console.warn('Failed to flush queued command', e)
          }
        }
      } catch (e) {
        console.error('Background sync failed', e)
      }
    })())
  }
})

// Optional: respond to fetch events for runtime caching
self.addEventListener('fetch', (event) => {
  // let the network handle it; caching is handled by PWA plugin or later enhancements
})
