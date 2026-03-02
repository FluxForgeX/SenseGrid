import { useState, useEffect, useRef } from 'react'
import { FiCamera, FiCameraOff, FiMaximize2, FiMinimize2, FiRefreshCw } from 'react-icons/fi'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

/**
 * CameraFeed - Live ESP32-CAM stream viewer component
 * 
 * Displays real-time MJPEG stream from ESP32-CAM via backend proxy.
 * Supports fullscreen mode, auto-reconnect, and status monitoring.
 */
export default function CameraFeed({ className = '' }) {
  const [isOnline, setIsOnline] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [error, setError] = useState(null)
  const [retryCount, setRetryCount] = useState(0)
  const imgRef = useRef(null)
  const containerRef = useRef(null)

  // Get auth token from localStorage
  const getToken = () => localStorage.getItem('token') || localStorage.getItem('authToken') || ''

  // Stream URL with token for authentication
  const getStreamUrl = () => `${API_URL}/camera/stream?token=${getToken()}&_t=${Date.now()}`

  // Check camera status
  const checkStatus = async () => {
    try {
      const token = getToken()
      if (!token) {
        setError('Not authenticated')
        setIsOnline(false)
        return
      }
      
      const response = await fetch(`${API_URL}/camera/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      if (response.ok) {
        const data = await response.json()
        setIsOnline(data.status === 'online')
        if (data.status !== 'online') {
          setError('Camera offline')
        } else {
          setError(null)
        }
      } else {
        setIsOnline(false)
        setError('Server error')
      }
    } catch (err) {
      setIsOnline(false)
      setError('Cannot connect to server')
    }
  }

  useEffect(() => {
    checkStatus()
    const interval = setInterval(checkStatus, 30000) // Check every 30s
    return () => clearInterval(interval)
  }, [])

  // Handle image load success
  const handleLoad = () => {
    setIsLoading(false)
    setIsOnline(true)
    setError(null)
    setRetryCount(0)
  }

  // Handle image load error
  const handleError = () => {
    setIsLoading(false)
    setIsOnline(false)
    
    // Auto-retry up to 3 times
    if (retryCount < 3) {
      setTimeout(() => {
        setRetryCount(prev => prev + 1)
        refreshStream()
      }, 2000)
    } else {
      setError('Camera stream unavailable')
    }
  }

  // Refresh stream
  const refreshStream = () => {
    setIsLoading(true)
    setError(null)
    if (imgRef.current) {
      imgRef.current.src = getStreamUrl()
    }
  }

  // Toggle fullscreen
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  // Handle fullscreen change events
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  // Start stream on mount
  useEffect(() => {
    if (imgRef.current && getToken()) {
      imgRef.current.src = getStreamUrl()
    }
  }, [])

  return (
    <div 
      ref={containerRef}
      className={`relative bg-gray-900 rounded-xl overflow-hidden shadow-lg ${className} ${isFullscreen ? 'fixed inset-0 z-50' : ''}`}
    >
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between p-3 bg-gradient-to-b from-black/70 to-transparent">
        <div className="flex items-center gap-2">
          {isOnline ? (
            <FiCamera className="text-green-400" size={18} />
          ) : (
            <FiCameraOff className="text-red-400" size={18} />
          )}
          <span className="text-white text-sm font-medium">
            {isOnline ? 'Security Camera' : 'Camera Offline'}
          </span>
          {isOnline && !isLoading && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-red-600 rounded text-xs text-white font-medium">
              <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
              LIVE
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-1">
          <button
            onClick={refreshStream}
            className="p-2 text-white/80 hover:text-white hover:bg-white/20 rounded-lg transition"
            title="Refresh stream"
            aria-label="Refresh camera stream"
          >
            <FiRefreshCw className={isLoading ? 'animate-spin' : ''} size={18} />
          </button>
          <button
            onClick={toggleFullscreen}
            className="p-2 text-white/80 hover:text-white hover:bg-white/20 rounded-lg transition"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          >
            {isFullscreen ? <FiMinimize2 size={18} /> : <FiMaximize2 size={18} />}
          </button>
        </div>
      </div>

      {/* Video Stream Container */}
      <div className={`relative bg-gray-800 ${isFullscreen ? 'h-full flex items-center justify-center' : 'aspect-video'}`}>
        {/* Loading State */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-800 z-5">
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-gray-400 text-sm">Connecting to camera...</span>
              {retryCount > 0 && (
                <span className="text-gray-500 text-xs">Retry {retryCount}/3</span>
              )}
            </div>
          </div>
        )}
        
        {/* Error State */}
        {error && !isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-800 z-5">
            <div className="flex flex-col items-center gap-3 text-center p-4">
              <FiCameraOff className="w-12 h-12 text-gray-500" />
              <span className="text-gray-400">{error}</span>
              <p className="text-gray-500 text-xs max-w-xs">
                Make sure ESP32-CAM is powered on and connected to the same network
              </p>
              <button
                onClick={() => { setRetryCount(0); refreshStream(); }}
                className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg transition text-sm"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* Camera Stream Image */}
        <img
          ref={imgRef}
          alt="Live camera feed"
          className={`w-full h-full object-contain ${isLoading || error ? 'opacity-0' : 'opacity-100'}`}
          onLoad={handleLoad}
          onError={handleError}
        />
      </div>

      {/* Status Bar */}
      <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/70 to-transparent">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'}`} />
            ESP32-CAM
          </span>
          <span>{new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  )
}
