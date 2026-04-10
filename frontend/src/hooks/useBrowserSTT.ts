/**
 * Browser-native STT hook — wraps SpeechRecognition (Chrome).
 * Ref: OpenMAIC lib/hooks/use-browser-asr.ts
 */
import { useState, useCallback, useRef, useEffect } from 'react'

interface UseBrowserSTTReturn {
  start: () => void
  stop: () => void
  listening: boolean
  transcript: string
  interimTranscript: string
  supported: boolean
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

export function useBrowserSTT(onFinal?: (text: string) => void): UseBrowserSTTReturn {
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [interimTranscript, setInterimTranscript] = useState('')
  const supported = !!SpeechRecognition
  const recRef = useRef<InstanceType<typeof SpeechRecognition> | null>(null)
  const onFinalRef = useRef(onFinal)
  onFinalRef.current = onFinal

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recRef.current) {
        try { recRef.current.stop() } catch { /* ignore */ }
      }
    }
  }, [])

  const start = useCallback(() => {
    if (!supported) return
    // Stop any existing recognition
    if (recRef.current) {
      try { recRef.current.stop() } catch { /* ignore */ }
    }

    const rec = new SpeechRecognition()
    rec.lang = 'zh-CN'
    rec.continuous = false       // Single utterance
    rec.interimResults = true    // Show partial results
    rec.maxAlternatives = 1

    let finalText = ''

    rec.onstart = () => {
      setListening(true)
      setTranscript('')
      setInterimTranscript('')
    }

    rec.onresult = (event: { results: SpeechRecognitionResultList }) => {
      let interim = ''
      let final_ = ''
      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          final_ += result[0].transcript
        } else {
          interim += result[0].transcript
        }
      }
      if (final_) {
        finalText = final_
        setTranscript(final_)
      }
      setInterimTranscript(interim)
    }

    rec.onend = () => {
      setListening(false)
      setInterimTranscript('')
      if (finalText && onFinalRef.current) {
        onFinalRef.current(finalText)
      }
    }

    rec.onerror = () => {
      setListening(false)
      setInterimTranscript('')
    }

    recRef.current = rec
    rec.start()
  }, [supported])

  const stop = useCallback(() => {
    if (recRef.current) {
      try { recRef.current.stop() } catch { /* ignore */ }
    }
  }, [])

  return { start, stop, listening, transcript, interimTranscript, supported }
}
