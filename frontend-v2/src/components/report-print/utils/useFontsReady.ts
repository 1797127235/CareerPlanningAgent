import { useEffect, useState } from 'react'

export function useFontsReady() {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    if (!document.fonts) {
      setReady(true)
      return
    }
    document.fonts.ready.then(() => setReady(true))
  }, [])
  return ready
}
