import React from 'react'
import RoomGrid from './components/RoomGrid'
import NotificationBell from './components/NotificationBell'
import useOnlineStatus from './hooks/useOnlineStatus'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export default function App() {
  const online = useOnlineStatus()

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">SenseGrid</h1>
          <div className="flex items-center space-x-4">
            <div className="text-sm">{online ? <span className="text-green-600">Online</span> : <span className="text-red-500">Offline</span>}</div>
            <NotificationBell />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-4">
        <RoomGrid apiBase={API_BASE} />
      </main>
    </div>
  )
}
