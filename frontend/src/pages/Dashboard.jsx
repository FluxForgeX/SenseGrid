import React, { useState, useEffect } from 'react'
import RoomGrid from '../components/RoomGrid'
import NotificationBell from '../components/NotificationBell'
import useOnlineStatus from '../hooks/useOnlineStatus'
import useStore from '../store/useStore'
import { useNavigate } from 'react-router-dom'
import { FaPlus, FaSignOutAlt } from 'react-icons/fa'
import { motion, AnimatePresence } from 'framer-motion'
import { fetchRooms, createRoom } from '../services/api'
import { toast } from 'react-toastify'

export default function Dashboard() {
  const online = useOnlineStatus()
  const { user, logout, addRoom, setRooms } = useStore()
  const navigate = useNavigate()
  const [isAddingRoom, setIsAddingRoom] = useState(false)
  const [newRoomName, setNewRoomName] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadRooms()
  }, [])

  const loadRooms = async () => {
    try {
      const rooms = await fetchRooms()
      setRooms(rooms)
    } catch (err) {
      console.error('Failed to fetch rooms:', err)
      if (err.response?.status === 401) {
        toast.error('Session expired. Please login again.')
        logout()
        navigate('/login')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('authToken')
    logout()
    toast.info('Logged out successfully')
    navigate('/')
  }

  const handleAddRoom = async (e) => {
    e.preventDefault()
    if (newRoomName.trim()) {
      const id = newRoomName.toLowerCase().replace(/\s+/g, '-')
      const roomData = {
        roomId: id,
        roomName: newRoomName,
        deviceId: `dev-${id}`,
        sensors: { temperature: 20, humidity: 50, gas: 0, flame: 0 },
        actions: { temperature: 'OFF' },
        lastSeen: Date.now()
      }
      
      try {
        const createdRoom = await createRoom(roomData)
        addRoom(createdRoom)
        toast.success(`Room "${newRoomName}" added successfully!`)
        setNewRoomName('')
        setIsAddingRoom(false)
      } catch (err) {
        const message = err.response?.data?.detail || 'Failed to add room'
        toast.error(message)
      }
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="bg-white shadow sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-teal-600">SenseGrid</h1>
            <span className="text-sm text-gray-500 hidden md:inline">Welcome, {user?.name || 'User'}</span>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="text-sm font-medium px-3 py-1 rounded-full bg-gray-100">
              {online ? <span className="text-green-600 flex items-center gap-2">● Online</span> : <span className="text-red-500 flex items-center gap-2">● Offline</span>}
            </div>
            <NotificationBell />
            <button onClick={handleLogout} className="text-gray-500 hover:text-red-500 transition" title="Logout">
              <FaSignOutAlt size={20} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-4">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800">My Home</h2>
          <button 
            onClick={() => setIsAddingRoom(true)}
            className="flex items-center gap-2 bg-teal-500 hover:bg-teal-600 text-white px-4 py-2 rounded-lg transition shadow-md"
          >
            <FaPlus /> Add Room
          </button>
        </div>

        <AnimatePresence>
          {isAddingRoom && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-6 overflow-hidden"
            >
              <form onSubmit={handleAddRoom} className="bg-white p-4 rounded-lg shadow border border-gray-200 flex gap-4 items-center">
                <input 
                  type="text" 
                  value={newRoomName}
                  onChange={(e) => setNewRoomName(e.target.value)}
                  placeholder="Enter room name (e.g. Guest Room)"
                  className="flex-grow border border-gray-300 rounded px-4 py-2 focus:outline-none focus:border-teal-500"
                  autoFocus
                />
                <button type="submit" className="bg-teal-500 text-white px-4 py-2 rounded hover:bg-teal-600">Add</button>
                <button type="button" onClick={() => setIsAddingRoom(false)} className="text-gray-500 hover:text-gray-700">Cancel</button>
              </form>
            </motion.div>
          )}
        </AnimatePresence>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-teal-600"></div>
            <p className="mt-4 text-gray-600">Loading rooms...</p>
          </div>
        ) : (
          <RoomGrid />
        )}
      </main>
    </div>
  )
}
