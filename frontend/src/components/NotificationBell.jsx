import React, { useState, useEffect } from 'react'
import { FaBell } from 'react-icons/fa'
import IntruderModal from './IntruderModal'
import { useSocket } from '../services/socket'

export default function NotificationBell() {
  const [unread, setUnread] = useState([])
  const [open, setOpen] = useState(false)
  const socket = useSocket()

  useEffect(() => {
    if (!socket) return
    socket.on('intruder:alert', alert => {
      setUnread(u => [alert, ...u])
    })
    return () => socket.off('intruder:alert')
  }, [socket])

  return (
    <div className="relative">
      <button aria-label="Notifications" onClick={() => setOpen(true)} className="relative p-2 rounded-full hover:bg-gray-100">
        <FaBell />
        {unread.length > 0 && <span className="absolute -top-1 -right-1 bg-red-600 text-white rounded-full text-xs px-1">{unread.length}</span>}
      </button>
      <IntruderModal open={open} onClose={() => setOpen(false)} alerts={unread} setAlerts={setUnread} />
    </div>
  )
}
