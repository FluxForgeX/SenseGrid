import { useEffect, useState } from 'react'

export default function useInstallPrompt() {
  const [deferred, setDeferred] = useState(null)

  useEffect(() => {
    function handler(e) {
      e.preventDefault()
      setDeferred(e)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  return {
    prompt: deferred ? () => deferred.prompt() : null,
    available: !!deferred
  }
}
