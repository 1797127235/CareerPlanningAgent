import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Kicker } from '@/components/editorial'
import { ChatBubble } from '@/components/coach-v2'
import { postChat } from '@/api/coach'
import type { ChatMessage } from '@/types/coach'

export default function CoachChatPage() {
  const [searchParams] = useSearchParams()
  const autoSentRef = useRef(false)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streaming, setStreaming] = useState(false)
  const [streamBuffer, setStreamBuffer] = useState('')
  const [input, setInput] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  const send = async (text: string) => {
    if (!text.trim()) return
    setMessages((prev) => [...prev, { role: 'user', content: text.trim() }])
    setStreaming(true)
    setStreamBuffer('')
    setErrorMsg('')

    let buffer = ''
    try {
      await postChat({ message: text.trim() }, (chunk) => {
        buffer += chunk
        setStreamBuffer(buffer)
      })
      setMessages((prev) => [...prev, { role: 'assistant', content: buffer }])
    } catch (err) {
      const msg = err instanceof Error ? err.message : '发送失败，请重试'
      setErrorMsg(msg)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `**出错了** — ${msg}` },
      ])
    } finally {
      setStreamBuffer('')
      setStreaming(false)
    }
  }

  useEffect(() => {
    const prompt = searchParams.get('prompt')
    if (prompt && !autoSentRef.current) {
      autoSentRef.current = true
      send(prompt)
    }
  }, [searchParams])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || streaming) return
    setInput('')
    send(text)
  }

  return (
    <main className="min-h-screen bg-[var(--bg-paper)] flex flex-col text-[var(--ink-1)]">
      <div className="flex-1 max-w-[720px] mx-auto w-full px-6 md:px-12 lg:px-20 py-16">
        <Kicker>CONVERSATION · 对话</Kicker>
        <h1 className="font-display font-medium text-[length:var(--fs-display-md)] leading-[var(--lh-display)] tracking-tight">
          和教练聊聊
        </h1>

        <div className="mt-10 space-y-6">
          {messages.map((m, i) => (
            <ChatBubble key={i} role={m.role} text={m.content} />
          ))}
          {streaming && streamBuffer && (
            <ChatBubble role="assistant" text={streamBuffer} streaming />
          )}
          {errorMsg && !streaming && (
            <p className="text-[length:var(--fs-body-sm)] text-[var(--ember)]">{errorMsg}</p>
          )}
        </div>
      </div>

      <div className="sticky bottom-0 bg-[var(--bg-paper)] border-t border-[var(--line)]">
        <form
          onSubmit={handleSubmit}
          className="max-w-[720px] mx-auto px-6 py-4 flex gap-3"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="想到什么就写下来"
            disabled={streaming}
            className="flex-1 bg-transparent border border-[var(--line)] rounded-full px-5 py-3 font-serif italic text-[length:var(--fs-body)] text-[var(--ink-1)] placeholder:text-[var(--ink-3)] outline-none focus:border-[var(--chestnut)]/60 transition-colors"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="px-6 py-3 rounded-full bg-[var(--ink-1)] text-[var(--bg-paper)] text-[length:var(--fs-body)] font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {streaming ? '发送中…' : '发送'}
          </button>
        </form>
      </div>
    </main>
  )
}
