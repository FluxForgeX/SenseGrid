import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useStore from '../store/useStore'
import { motion } from 'framer-motion'
import { FaCouch, FaUtensils, FaBed, FaCar, FaBook, FaBath, FaPlus, FaMinus } from 'react-icons/fa'

const PREDEFINED_ROOMS = [
  { id: 'living-room', name: 'Living Room', icon: <FaCouch />, type: 'living' },
  { id: 'kitchen', name: 'Kitchen', icon: <FaUtensils />, type: 'kitchen' },
  { id: 'bedroom', name: 'Bedroom', icon: <FaBed />, type: 'bedroom' },
  { id: 'master-room', name: 'Master Room', icon: <FaBed />, type: 'bedroom' },
  { id: 'study-room', name: 'Study Room', icon: <FaBook />, type: 'study' },
  { id: 'garage', name: 'Garage', icon: <FaCar />, type: 'garage' },
  { id: 'bathroom', name: 'Bathroom', icon: <FaBath />, type: 'bathroom' },
]

export default function OnboardingPage() {
  const [roomCounts, setRoomCounts] = useState({})
  const setRooms = useStore(state => state.setRooms)
  const navigate = useNavigate()

  const updateCount = (roomId, delta) => {
    setRoomCounts(prev => {
      const current = prev[roomId] || 0
      const next = Math.max(0, current + delta)
      if (next === 0) {
        const { [roomId]: _, ...rest } = prev
        return rest
      }
      return { ...prev, [roomId]: next }
    })
  }

  const handleFinish = () => {
    const initialRooms = []
    
    Object.entries(roomCounts).forEach(([roomId, count]) => {
      const template = PREDEFINED_ROOMS.find(r => r.id === roomId)
      if (!template) return

      for (let i = 1; i <= count; i++) {
        const name = count > 1 ? `${template.name} ${i}` : template.name
        const uniqueId = `${roomId}-${Date.now()}-${i}`
        
        initialRooms.push({
          roomId: uniqueId,
          roomName: name,
          deviceId: `dev-${uniqueId}`,
          sensors: { temperature: 22, humidity: 45, gas: 0, flame: 0 },
          actions: { temperature: 'OFF' },
          lastSeen: Date.now()
        })
      }
    })
    
    setRooms(initialRooms)
    navigate('/dashboard')
  }

  const totalRooms = Object.values(roomCounts).reduce((a, b) => a + b, 0)

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-6">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-5xl w-full"
      >
        <h1 className="text-4xl font-bold mb-4 text-center">Setup Your Home</h1>
        <p className="text-gray-400 text-center mb-10">How many of each room do you have?</p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
          {PREDEFINED_ROOMS.map((room) => {
            const count = roomCounts[room.id] || 0
            return (
              <motion.div
                key={room.id}
                className={`p-4 rounded-xl border-2 flex items-center justify-between gap-4 transition-all ${
                  count > 0
                    ? 'border-teal-500 bg-teal-500/10' 
                    : 'border-gray-700 bg-gray-800'
                }`}
              >
                <div className="flex items-center gap-4">
                  <div className={`text-2xl ${count > 0 ? 'text-teal-400' : 'text-gray-500'}`}>{room.icon}</div>
                  <span className={`font-medium ${count > 0 ? 'text-white' : 'text-gray-400'}`}>{room.name}</span>
                </div>

                <div className="flex items-center gap-3 bg-gray-900 rounded-lg p-1">
                  <button 
                    onClick={() => updateCount(room.id, -1)}
                    className="w-8 h-8 flex items-center justify-center rounded hover:bg-gray-700 text-gray-400 hover:text-white transition"
                    disabled={count === 0}
                  >
                    <FaMinus size={12} />
                  </button>
                  <span className="w-6 text-center font-bold">{count}</span>
                  <button 
                    onClick={() => updateCount(room.id, 1)}
                    className="w-8 h-8 flex items-center justify-center rounded hover:bg-gray-700 text-gray-400 hover:text-white transition"
                  >
                    <FaPlus size={12} />
                  </button>
                </div>
              </motion.div>
            )
          })}
        </div>

        <div className="flex justify-center">
          <button 
            onClick={handleFinish}
            disabled={totalRooms === 0}
            className={`px-8 py-3 rounded-full font-bold text-lg transition ${
              totalRooms > 0 
                ? 'bg-teal-500 hover:bg-teal-600 text-white shadow-lg hover:shadow-teal-500/30' 
                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            }`}
          >
            Finish Setup ({totalRooms} rooms)
          </button>
        </div>
      </motion.div>
    </div>
  )
}
