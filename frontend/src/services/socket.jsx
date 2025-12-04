import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import { io } from 'socket.io-client'

const SocketContext = createContext(null)

export function SocketProvider({ children }) {
  const socketRef = useRef(null)
  const [socket, setSocket] = useState(null)

  useEffect(() => {
    const url = import.meta.env.VITE_WS_URL || 'http://localhost:8000'
    const s = io(url, { autoConnect: false, reconnection: true, reconnectionDelay: 2000 })
    socketRef.current = s
    setSocket(s)
    // Attempt connection but don't fail if socket.io endpoint missing
    s.connect()
    // Silent error handling — don't spam console if socket.io unavailable
    s.on('error', (err) => {
      console.debug('[socket] connection error (expected if backend socket.io not available):', err)
    })
    return () => s.disconnect()
  }, [])

  return <SocketContext.Provider value={socket}>{children}</SocketContext.Provider>
}

export function useSocket() {
  return useContext(SocketContext)
}

export default SocketContext
