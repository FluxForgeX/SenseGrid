import React, { useState } from 'react'
import { sendAlertAction } from '../services/api'

export default function IntruderModal({ open, onClose, alerts = [], setAlerts }) {
  const [selected, setSelected] = useState(null)

  if (!open) return null

  async function action(alertId, actionType) {
    try {
      await sendAlertAction(alertId, actionType)
      // optimistic remove
      setAlerts(prev => prev.filter(a => a.alertId !== alertId))
      setSelected(null)
    } catch (e) {
      console.error('Action failed', e)
      alert('Action failed')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-2xl p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Intruder Alerts</h3>
          <button onClick={onClose} className="text-gray-600">Close</button>
        </div>

        <div className="mt-4 grid gap-3">
          {alerts.length === 0 && <div className="text-sm text-gray-500">No alerts</div>}
          {alerts.map(alert => (
            <div key={alert.alertId} className="flex items-center space-x-3">
              <img src={alert.snapshotUrl} alt="thumb" className="w-20 h-16 object-cover rounded" />
              <div className="flex-1">
                <div className="font-medium">{new Date(alert.ts).toLocaleString()}</div>
                <div className="text-sm text-gray-500">Home: {alert.homeId}</div>
              </div>
              <div className="space-x-2">
                <button onClick={() => action(alert.alertId, 'allow')} className="px-3 py-1 bg-green-600 text-white rounded">ALLOW ENTRY</button>
                <button onClick={() => action(alert.alertId, 'deny')} className="px-3 py-1 bg-red-600 text-white rounded">DENY</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
