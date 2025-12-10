import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useStore from '../store/useStore'
import { motion } from 'framer-motion'
import { FaCouch, FaUtensils, FaBed, FaCar, FaBook, FaBath } from 'react-icons/fa'

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
  const [selectedRooms, setSelectedRooms] = useState([])
  const setRooms = useStore(state => state.setRooms)
  const navigate = useNavigate()

  const toggleRoom = (room) => {
    if (selectedRooms.find(r => r.id === room.id)) {
      setSelectedRooms(selectedRooms.filter(r => r.id !== room.id))
    } else {
      setSelectedRooms([...selectedRooms, room])
    }
  }

  const handleFinish = () => {
    // Transform to the format expected by RoomGrid/Store
    const initialRooms = selectedRooms.map(r => ({
      roomId: r.id,
      roomName: r.name,
      deviceId: `dev-${r.id}`, // Mock device ID
      sensors: { temperature: 22, humidity: 45, gas: 0, flame: 0 },
      actions: { temperature: 'OFF' },
      lastSeen: Date.now()
    }))
    
    setRooms(initialRooms)
    navigate('/dashboard')
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-6">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-4xl w-full"
      >
        <h1 className="text-4xl font-bold mb-4 text-center">Setup Your Home</h1>
        <p className="text-gray-400 text-center mb-10">Select the rooms you want to monitor. You can always change this later.</p>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-10">
          {PREDEFINED_ROOMS.map((room) => {
            const isSelected = selectedRooms.find(r => r.id === room.id)
            return (
              <motion.button
                key={room.id}
                whileTap={{ scale: 0.95 }}
                onClick={() => toggleRoom(room)}
                className={`p-6 rounded-xl border-2 flex flex-col items-center justify-center gap-4 transition-all ${
                  isSelected 
                    ? 'border-teal-500 bg-teal-500/20 text-teal-400' 
                    : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'
                }`}
              >
                <div className="text-3xl">{room.icon}</div>
                <span className="font-medium">{room.name}</span>
              </motion.button>
            )
          })}
        </div>

        <div className="flex justify-center">
          <button 
            onClick={handleFinish}
            disabled={selectedRooms.length === 0}
            className={`px-8 py-3 rounded-full font-bold text-lg transition ${
              selectedRooms.length > 0 
                ? 'bg-teal-500 hover:bg-teal-600 text-white shadow-lg hover:shadow-teal-500/30' 
                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            }`}
          >
            Finish Setup
          </button>
        </div>
      </motion.div>
    </div>
  )
}
