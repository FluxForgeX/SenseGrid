import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import './styles.css'
import { SocketProvider } from './services/socket'

// PWA install prompt hook will handle the beforeinstallprompt event
createRoot(document.getElementById('root')).render(
  <SocketProvider>
    <>
      <App />
      <ToastContainer 
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="colored"
        style={{ zIndex: 99999 }}
      />
    </>
  </SocketProvider>
)

// Register custom service worker for Background Sync (if supported)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      await navigator.serviceWorker.register('/sw.js')
      console.log('Service worker registered')
    } catch (e) {
      console.warn('SW registration failed:', e)
    }
  })
}
