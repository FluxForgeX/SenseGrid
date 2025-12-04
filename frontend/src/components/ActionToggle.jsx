/**
 * ActionToggle Component
 * Per-sensor action toggle with optimistic UI, queued state, and accessibility
 *
 * Props:
 *   roomId: string
 *   sensor: 'temperature'|'humidity'|'gas'|'flame'
 *   state: 'ON'|'OFF' (current state from server/props)
 *   auto: boolean (auto mode active)
 *   queued: boolean (command queued offline)
 *   onToggle: (sensor, newValue) => Promise<boolean>
 *   disabled: boolean (disables interaction)
 */

import React, { useState, useEffect, useRef } from 'react'

export default function ActionToggle({
  roomId,
  sensor,
  state = 'OFF',
  auto = false,
  queued = false,
  disabled = false,
  onToggle
}) {
  const [loading, setLoading] = useState(false)
  const [visualState, setVisualState] = useState(state)
  const [error, setError] = useState(false)
  const lockRef = useRef(false)

  // Keep visualState in sync with incoming state prop
  useEffect(() => {
    setVisualState(state)
    setError(false)
  }, [state])

  // Debounce keyboard presses to avoid double-click
  async function handleToggleClick() {
    if (disabled || loading || lockRef.current) {
      return
    }

    lockRef.current = true
    setTimeout(() => {
      lockRef.current = false
    }, 600)

    const next = visualState === 'ON' ? 'OFF' : 'ON'
    setVisualState(next)
    setLoading(true)
    setError(false)

    try {
      if (typeof onToggle === 'function') {
        const result = await onToggle(sensor, next)
        // onToggle returns true if successful
        if (result === false) {
          // If it failed, revert visual state
          setVisualState(prev => (prev === 'ON' ? 'OFF' : 'ON'))
          setError(true)
          setTimeout(() => setError(false), 3000) // Clear error after 3s
        }
      }
    } catch (err) {
      console.error('[ActionToggle] onToggle threw', err)
      setVisualState(prev => (prev === 'ON' ? 'OFF' : 'ON'))
      setError(true)
      setTimeout(() => setError(false), 3000)
    } finally {
      setLoading(false)
    }
  }

  // Handle keyboard Enter/Space
  function handleKeyDown(e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleToggleClick()
    }
  }

  const isOn = visualState === 'ON'
  const buttonClasses = `
    min-h-touch min-w-touch px-4 py-2 rounded font-medium
    transition-all duration-150 ease-out
    focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600
    disabled:opacity-50 disabled:cursor-not-allowed
    ${isOn ? 'bg-teal-500 text-white hover:bg-teal-600 active:scale-95' : 'bg-gray-200 text-gray-800 hover:bg-gray-300 active:scale-95'}
    ${error ? 'bg-red-500 text-white' : ''}
    ${loading ? 'opacity-75' : ''}
  `

  const badgeClasses = `
    inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold
    transition-opacity duration-200
  `

  return (
    <div className="flex items-center justify-end gap-2 py-1 sm:py-0">
      {/* Auto badge */}
      {auto && (
        <span className={`${badgeClasses} bg-yellow-100 text-yellow-800`} role="status">
          Auto
        </span>
      )}

      {/* Queued badge - only show when truly queued (not after temporary failure) */}
      {queued && !error && (
        <span
          className={`${badgeClasses} bg-orange-100 text-orange-800 animate-pulse`}
          role="status"
          aria-label="Queued for sync"
        >
          Queued
        </span>
      )}

      {/* Error badge - temporary */}
      {error && (
        <span className={`${badgeClasses} bg-red-100 text-red-800`} role="alert">
          Error
        </span>
      )}

      {/* Toggle button */}
      <button
        type="button"
        aria-pressed={isOn}
        aria-label={`${sensor}: ${isOn ? 'ON' : 'OFF'}. ${auto ? 'Auto mode enabled.' : ''} ${queued ? 'Queued for sync.' : ''} ${error ? 'Error occurred.' : ''}`}
        onClick={handleToggleClick}
        onKeyDown={handleKeyDown}
        disabled={disabled || loading}
        className={buttonClasses}
      >
        <span className="text-sm sm:text-base">
          {loading ? '...' : isOn ? 'ON' : 'OFF'}
        </span>
      </button>
    </div>
  )
}
