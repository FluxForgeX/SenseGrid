import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react()
  ],
  define: {
    'process.env': {}
  },
  // Server configuration for localhost and Raspberry Pi
  server: {
    host: true, // Listen on all addresses (0.0.0.0)
    port: 5173,
    strictPort: false, // Try next port if 5173 is busy
  },
  preview: {
    host: true,
    port: 4173,
  }
})
