import React from 'react'

export default function SensorRow({ icon, name, value, unit }) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center space-x-3">
        <div className="text-sky-500">{icon}</div>
        <div>
          <div className="text-sm font-medium">{name}</div>
          <div className="text-xs text-gray-500">{value}{unit ? ` ${unit}` : ''}</div>
        </div>
      </div>
    </div>
  )
}
