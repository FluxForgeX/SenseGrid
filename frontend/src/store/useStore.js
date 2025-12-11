import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const useStore = create(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      rooms: [],
      
      login: (userData) => set({ user: userData, isAuthenticated: true }),
      logout: () => set({ user: null, isAuthenticated: false, rooms: [] }),
      
      setRooms: (rooms) => set({ rooms }),
      addRoom: (room) => set((state) => ({ rooms: [...state.rooms, room] })),
      removeRoom: (roomId) => set((state) => ({ rooms: state.rooms.filter(r => r.roomId !== roomId) })),
      updateRoom: (roomId, updates) => set((state) => ({
        rooms: state.rooms.map(r => r.roomId === roomId ? { ...r, ...updates } : r)
      })),
      // Update a specific room action (for optimistic UI sync)
      updateRoomAction: (roomId, sensor, value) => set((state) => ({
        rooms: state.rooms.map(r => 
          r.roomId === roomId 
            ? { ...r, actions: { ...(r.actions || {}), [sensor]: value } }
            : r
        )
      })),
    }),
    {
      name: 'sensegrid-storage', // unique name
    }
  )
)

export default useStore
