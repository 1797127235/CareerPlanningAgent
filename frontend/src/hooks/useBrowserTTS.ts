/**
 * Browser-native TTS hook — wraps window.speechSynthesis.
 * Ref: OpenMAIC lib/hooks/use-browser-tts.ts
 */
import { useState, useCallback, useRef, useEffect } from 'react'

interface UseBrowserTTSReturn {
  speak: (text: string) => void
  pause: () => void
  resume: () => void
  cancel: () => void
  speaking: boolean
  paused: boolean
  supported: boolean
}

/** Strip markdown bold / HTML tags so TTS reads clean text */
function cleanForSpeech(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/\n{2,}/g, '。')
    .replace(/\n/g, '，')
}

export function useBrowserTTS(): UseBrowserTTSReturn {
  const [speaking, setSpeaking] = useState(false)
  const [paused, setPaused] = useState(false)
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window
  const utterRef = useRef<SpeechSynthesisUtterance | null>(null)

  // Cancel on unmount
  useEffect(() => {
    return () => {
      if (supported) window.speechSynthesis.cancel()
    }
  }, [supported])

  const speak = useCallback(
    (text: string) => {
      if (!supported) return
      // Cancel any ongoing speech
      window.speechSynthesis.cancel()

      const cleaned = cleanForSpeech(text)
      const utter = new SpeechSynthesisUtterance(cleaned)
      utter.lang = 'zh-CN'
      utter.rate = 1.1
      utter.pitch = 1.0

      // Try to pick a good Chinese voice
      const voices = window.speechSynthesis.getVoices()
      const zhVoice = voices.find(
        (v) => v.lang.startsWith('zh') && v.name.includes('Xiaoxiao'),
      ) ?? voices.find(
        (v) => v.lang.startsWith('zh-CN'),
      ) ?? voices.find(
        (v) => v.lang.startsWith('zh'),
      )
      if (zhVoice) utter.voice = zhVoice

      utter.onstart = () => {
        setSpeaking(true)
        setPaused(false)
      }
      utter.onend = () => {
        setSpeaking(false)
        setPaused(false)
      }
      utter.onerror = () => {
        setSpeaking(false)
        setPaused(false)
      }

      utterRef.current = utter
      window.speechSynthesis.speak(utter)
    },
    [supported],
  )

  const pause = useCallback(() => {
    if (!supported) return
    window.speechSynthesis.pause()
    setPaused(true)
  }, [supported])

  const resume = useCallback(() => {
    if (!supported) return
    window.speechSynthesis.resume()
    setPaused(false)
  }, [supported])

  const cancel = useCallback(() => {
    if (!supported) return
    window.speechSynthesis.cancel()
    setSpeaking(false)
    setPaused(false)
  }, [supported])

  return { speak, pause, resume, cancel, speaking, paused, supported }
}
