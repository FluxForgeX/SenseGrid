import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'SenseGrid',
        short_name: 'SenseGrid',
        start_url: '/',
        display: 'standalone',
        background_color: '#ffffff',
        theme_color: '#0ea5a4',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' }
        ]
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: /\/api\//,
            handler: 'NetworkFirst',
          },
          {
            urlPattern: /\/icons\//,
            handler: 'CacheFirst',
          }
        ]
      }
    })
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
