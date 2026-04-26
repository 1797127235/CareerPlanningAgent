import { useState, useEffect, useRef, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUp, Compass, X, MessageSquare, Plus, Trash2, Volume2, VolumeX, PanelRightClose, RotateCcw, Search, CheckCircle2 } from 'lucide-react'
import { useNavigate, useLocation } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChat } from '@/hooks/useChat'
import type { ChatMessage, CardData, JdCardData, MarketCardData } from '@/hooks/useChat'
import { API_BASE } from '@/api/client'
import { useSessions } from '@/hooks/useSessions'
import { useBrowserTTS } from '@/hooks/useBrowserTTS'
import { useCoachTriggerListener } from '@/hooks/useCoachTrigger'
import { createApplication } from '@/api/applications'

/* ── Placeholder rotation texts ── */
const placeholders = [
  '我大三计算机专业，不知道该找什么工作...',
  '粘贴一段 JD，帮你分析匹配度和缺口...',
  '前端和后端哪个更适合我？',
  '这个岗位未来会被 AI 替代吗？',
  '帮我生成一份职业规划报告...',
]

/* ── Chip type ── */
interface Chip {
  label: string
  prompt: string
}

const defaultChips: Chip[] = [
  { label: '我适合什么方向', prompt: '根据我的技能，推荐适合的岗位方向' },
  { label: '诊断一份 JD', prompt: '诊断 JD 匹配度' },
  { label: '练一道面试题', prompt: '出一道面试题' },
  { label: '聊聊职业规划', prompt: '我是计算机专业学生，不知道该往哪个方向发展' },
]

/* ── Markdown renderer for AI messages ── */
function AIMarkdown({ text }: { text: string }) {
  return (
    <div className="prose-ai">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  )
}

/* ═══════════════════════════════════════════════
   ChatPanel — self-contained, collapsible right panel
   ═══════════════════════════════════════════════ */
interface ChatPanelProps {
  open: boolean
  onClose: () => void
  mode?: 'panel' | 'float'  // panel = right sidebar, float = mobile popup
}

/* ── Route → label map for page context ── */
const routeLabels: Record<string, string> = {
  '/': '首页',
  '/profile': '能力画像',
  '/graph': '岗位图谱',
  '/growth-log': '成长档案',
  '/report': '职业报告',
}

function getPageLabel(pathname: string): string {
  if (routeLabels[pathname]) return routeLabels[pathname]
  if (pathname.startsWith('/roles/')) return '岗位详情'
  if (pathname.startsWith('/coach/result/')) return '教练分析报告'
  if (pathname.startsWith('/profile/match/')) return '匹配详情'
  return '其他'
}

export function ChatPanel({ open, onClose, mode = 'float' }: ChatPanelProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { sessions, grouped: sessionGroups, refetch: refetchSessions, deleteSession } = useSessions()
  const { messages, isStreaming, currentStreamText, currentStreamAgent, sessionId, sendMessage, clearMessages, loadSession, setPageContext } = useChat(refetchSessions)

  /* ── Sync page context on route change ── */
  useEffect(() => {
    setPageContext({
      route: location.pathname,
      label: getPageLabel(location.pathname),
    })
  }, [location.pathname, setPageContext])

  /* ── Listen for coach trigger events ── */
  useCoachTriggerListener(sendMessage, isStreaming)

  const [inputText, setInputText] = useState('')
  const [placeholderIdx, setPlaceholderIdx] = useState(0)
  const [placeholderFading, setPlaceholderFading] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  /* ── Greeting data (fetched on panel open) ── */
  interface GreetingData { greeting: string; chips: Chip[]; market_card?: MarketCardData; processing?: boolean; has_profile?: boolean }
  const [greetingData, setGreetingData] = useState<GreetingData | null>(null)

  useEffect(() => {
    if (!open) return
    const token = localStorage.getItem('token')
    if (!token) return

    let pollTimer: ReturnType<typeof setTimeout> | null = null

    const fetchGreeting = () => {
      fetch(`${API_BASE}/chat/greeting`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then(r => r.ok ? r.json() : null)
        .then((data: GreetingData | null) => {
          if (!data) return
          setGreetingData(data)
          // Backend signals background processing not done — auto-refresh in 8s
          if (data.processing) {
            pollTimer = setTimeout(fetchGreeting, 8000)
          }
        })
        .catch(() => {/* silent fail */})
    }

    fetchGreeting()
    return () => { if (pollTimer) clearTimeout(pollTimer) }
  }, [open])

  /* ── Page-aware tip bar ── */
  const [pageTip, setPageTip] = useState<{ text: string; prompt: string } | null>(null)
  const dismissedTipRef = useRef<string>('')

  useEffect(() => {
    const tips: Record<string, { text: string; prompt: string }> = {
      '/profile': { text: '画像页 — 想诊断技能缺口？粘贴一段目标 JD 试试', prompt: '诊断 JD 匹配度' },
      '/graph': { text: '图谱页 — 点击感兴趣的岗位，我帮你分析转型路径', prompt: '帮我探索岗位图谱' },
      '/growth-log': { text: '成长档案 — 想知道下一步该做什么？', prompt: '分析我的成长数据，推荐下一步行动' },
      '/report': { text: '报告页 — 想升级报告？可以粘 JD 或补档案，我来帮你拉通。', prompt: '基于我的画像和成长数据帮我规划下一步' },
    }
    const tip = tips[location.pathname]
    if (tip && dismissedTipRef.current !== location.pathname) {
      setPageTip(tip)
    } else {
      setPageTip(null)
    }
  }, [location.pathname])

  /* ── Voice: TTS + STT ── */
  const tts = useBrowserTTS()
  const [ttsPlayingId, setTtsPlayingId] = useState<string | null>(null)

  const handleTTSToggle = useCallback((msgId: string, text: string) => {
    if (tts.speaking && ttsPlayingId === msgId) {
      tts.cancel()
      setTtsPlayingId(null)
    } else {
      tts.cancel()
      setTtsPlayingId(msgId)
      tts.speak(text)
    }
  }, [tts, ttsPlayingId])

  // Reset ttsPlayingId when speech ends
  useEffect(() => {
    if (!tts.speaking) setTtsPlayingId(null)
  }, [tts.speaking])

  /* ── Drag state ── */
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null)
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null)

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const userScrolledUpRef = useRef(false)

  const inChat = messages.length > 0 || isStreaming

  /* ── Placeholder rotation ── */
  useEffect(() => {
    const timer = setInterval(() => {
      setPlaceholderFading(true)
      setTimeout(() => {
        setPlaceholderIdx((i) => (i + 1) % placeholders.length)
        setPlaceholderFading(false)
      }, 250)
    }, 3000)
    return () => clearInterval(timer)
  }, [])

  /* ── Auto-scroll (respect user manual scroll) ── */
  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    if (userScrolledUpRef.current) return
    el.scrollTop = el.scrollHeight
  }, [messages, currentStreamText])

  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60
    userScrolledUpRef.current = !nearBottom
  }, [])

  /* ── Drag handling ── */
  const onDragStart = useCallback((e: React.MouseEvent) => {
    const el = e.currentTarget.closest('[data-chat-panel]') as HTMLElement | null
    if (!el) return
    const rect = el.getBoundingClientRect()
    dragRef.current = { startX: e.clientX, startY: e.clientY, origX: rect.left, origY: rect.top }
    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return
      const dx = ev.clientX - dragRef.current.startX
      const dy = ev.clientY - dragRef.current.startY
      const nx = Math.max(0, Math.min(window.innerWidth - 380, dragRef.current.origX + dx))
      const ny = Math.max(0, Math.min(window.innerHeight - 100, dragRef.current.origY + dy))
      setPos({ x: nx, y: ny })
    }
    const onUp = () => {
      dragRef.current = null
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [])

  /* ── Textarea auto-resize ── */
  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }, [])

  /* ── Send ── */
  const handleSend = useCallback(() => {
    if (!inputText.trim()) return
    sendMessage(inputText)
    setInputText('')
    userScrolledUpRef.current = false
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }, [inputText, sendMessage])

  /* ── Keyboard ── */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  /* ── New chat ── */
  const handleNewChat = useCallback(() => {
    clearMessages()
    setInputText('')
    setShowHistory(false)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }, [clearMessages])

  /* ── Delete session ── */
  const handleSessionDelete = useCallback(async (id: number) => {
    await deleteSession(id)
    if (id === sessionId) clearMessages()
  }, [deleteSession, sessionId, clearMessages])

  /* ── Load session ── */
  const handleSessionSelect = useCallback((id: number) => {
    loadSession(id)
    setShowHistory(false)
  }, [loadSession])

  const hasText = inputText.trim().length > 0

  if (!open) return null

  const isPanel = mode === 'panel'

  const floatStyle: React.CSSProperties = !isPanel && pos
    ? { left: pos.x, top: pos.y, right: 'auto', bottom: 'auto' }
    : {}

  return (
    <div
      data-chat-panel
      style={isPanel ? undefined : floatStyle}
      className={
        isPanel
          ? 'flex flex-col h-full w-full bg-white/90'
          : `fixed z-50 w-[380px] h-[560px] max-h-[calc(100vh-48px)] flex flex-col bg-white/70 backdrop-blur-[24px] backdrop-saturate-[140%] border border-white/50 rounded-2xl shadow-[0_8px_40px_rgba(0,0,0,0.12),0_0_0_1px_rgba(0,0,0,0.04)] ${pos ? '' : 'bottom-6 right-6'}`
      }
    >
      {/* ── Header ── */}
      {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions */}
      <div
        onMouseDown={isPanel ? undefined : onDragStart}
        className={`h-12 flex items-center justify-between px-4 shrink-0 border-b border-black/[0.06] select-none ${isPanel ? '' : 'rounded-t-2xl cursor-grab active:cursor-grabbing'}`}
      >
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-[var(--chestnut)]" />
          <span className="text-[14px] font-semibold text-[#1F1F1F]">智析教练</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="p-1.5 text-[#A89B8C] hover:text-[#6B5E4F] hover:bg-[#F2EDE4] rounded-lg transition-colors active:scale-[0.92] cursor-pointer"
            title="对话历史"
          >
            <MessageSquare className="w-4 h-4" />
          </button>
          <button
            onClick={handleNewChat}
            className="p-1.5 text-[#A89B8C] hover:text-[#6B5E4F] hover:bg-[#F2EDE4] rounded-lg transition-colors active:scale-[0.92] cursor-pointer"
            title="新对话"
          >
            <Plus className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 text-[#A89B8C] hover:text-[#6B5E4F] hover:bg-[#F2EDE4] rounded-lg transition-colors active:scale-[0.92] cursor-pointer"
            title={isPanel ? '收起教练' : '关闭'}
          >
            {isPanel ? <PanelRightClose className="w-4 h-4" /> : <X className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* ── Session history dropdown ── */}
      <AnimatePresence>
        {showHistory && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-b border-black/[0.06] overflow-hidden"
          >
            <div className="max-h-48 overflow-y-auto py-2 px-3">
              {sessionGroups.length === 0 ? (
                <div className="text-[13px] text-[#A89B8C] text-center py-4">暂无对话记录</div>
              ) : (
                sessionGroups.map((group) => (
                  <div key={group.group}>
                    <div className="text-[11px] font-medium text-[#A89B8C]/70 px-2 pt-2 pb-1">{group.group}</div>
                    {group.items.map((item) => (
                      <div
                        key={item.id}
                        onClick={() => handleSessionSelect(item.id)}
                        className={`
                          flex items-center gap-2 h-8 px-2 rounded-lg text-[13px] cursor-pointer group transition-colors
                          ${item.id === sessionId
                            ? 'bg-white/60 text-[#1F1F1F]'
                            : 'text-[#8A7E6B] hover:text-[#3D352E] hover:bg-white/30'
                          }
                        `}
                      >
                        <span className="truncate flex-1">{item.title}</span>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleSessionDelete(item.id) }}
                          className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 p-0.5 rounded text-[#A89B8C] hover:text-red-500 transition-all shrink-0"
                          aria-label="删除会话"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Page-aware tip bar ── */}
      <AnimatePresence>
        {pageTip && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="flex items-center gap-2 px-3 py-2 bg-white/50 border-b border-white/40 text-[12px]">
              <span className="flex-1 text-[#8A7E6B] truncate">{pageTip.text}</span>
              <button
                onClick={() => { sendMessage(pageTip.prompt); setPageTip(null); dismissedTipRef.current = location.pathname }}
                className="shrink-0 px-2.5 py-1 rounded-lg bg-white/60 text-[#6B5E4F] font-medium hover:bg-white/80 border border-white/50 transition-colors cursor-pointer"
              >
                试试
              </button>
              <button
                onClick={() => { setPageTip(null); dismissedTipRef.current = location.pathname }}
                className="shrink-0 p-0.5 text-[#A89B8C] hover:text-[#6B5E4F] cursor-pointer"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Messages ── */}
      <div ref={scrollRef} onScroll={handleScroll} className="flex-1 overflow-y-auto px-4 py-4">
        {!inChat ? (
          /* Clean empty state */
          <div className="flex flex-col h-full select-none">
            <div className="flex-1" />
            {/* Greeting or default prompt */}
            <div className="px-2 mb-4">
              {greetingData ? (
                <div className="bg-white/60 rounded-xl p-3 border border-white/80 shadow-sm message-enter">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded-lg bg-[var(--chestnut)] flex items-center justify-center">
                      <Compass className="w-3.5 h-3.5 text-white" />
                    </div>
                    <span className="text-[12px] font-semibold text-[#8A7E6B]">智析教练</span>
                  </div>
                  <p className="text-[13px] text-[#6B5E4F] leading-relaxed whitespace-pre-line">{greetingData.greeting}</p>
                  {greetingData.market_card && (
                    <MarketCards cards={[greetingData.market_card]} />
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center text-center">
                  <Compass className="w-10 h-10 text-[var(--chestnut)]/30 mb-3" />
                  <p className="text-[13px] text-[#A89B8C]">随时可以开始对话</p>
                </div>
              )}
            </div>
            {/* Continue last conversation */}
            {sessions.length > 0 && (
              <div className="flex justify-center mb-3">
                <button
                  onClick={() => handleSessionSelect(sessions[0].id)}
                  className="flex items-center gap-2 px-4 py-2 text-[12px] text-[#8A7E6B] hover:text-[var(--chestnut)] bg-white/40 hover:bg-white/60 border border-white/50 hover:border-[var(--chestnut)]/20 rounded-xl transition-all active:scale-[0.97] cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span className="truncate max-w-[200px]">继续：{sessions[0].title}</span>
                </button>
              </div>
            )}
            <div className="flex flex-wrap justify-center gap-2 px-2">
              {(greetingData?.chips ?? defaultChips).map((chip) => (
                <button
                  key={chip.label}
                  onClick={() => sendMessage(chip.prompt)}
                  className="chip text-[12px] font-medium text-[var(--text-2)] hover:text-[var(--text-1)] active:scale-[0.97] transition-transform"
                >
                  {chip.label}
                </button>
              ))}
              {greetingData && !greetingData.has_profile && (
                <button
                  onClick={() => sendMessage('我没有简历，想通过对话建立画像')}
                  className="chip text-[12px] font-medium text-[var(--text-2)] hover:text-[var(--text-1)] active:scale-[0.97] transition-transform"
                >
                  没简历？对话建档
                </button>
              )}
            </div>
            <div className="flex-[2]" />
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <PanelBubble
                key={msg.id}
                message={msg}
                onTTSToggle={tts.supported ? handleTTSToggle : undefined}
                isTTSPlaying={tts.speaking && ttsPlayingId === msg.id}
                onCardClick={(card) => navigate(`/coach/result/${card.id}`)}
                onJdDiagnose={(jd) => sendMessage(
                  `请诊断这份JD的匹配度：\n\n${jd.full_text}`,
                  { job_url: jd.url, company: jd.source },
                )}
                onFollowUp={(text) => sendMessage(text)}
              />
            ))}

            {/* Streaming */}
            {isStreaming && currentStreamText && (() => {
              const sCfg = agentConfig[currentStreamAgent ?? ''] ?? agentConfig.coach_agent
              return (
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-1.5">
                    <div className={`w-6 h-6 rounded-lg ${sCfg.color} flex items-center justify-center text-white`}>
                      <Compass className="w-3.5 h-3.5" />
                    </div>
                    <span className="text-[12px] font-semibold text-[#8A7E6B]">{sCfg.name}</span>
                  </div>
                  <div className="bg-white/[0.38] backdrop-blur-[16px] border border-white/[0.35] text-[var(--text-1)] px-4 py-3 rounded-[4px_14px_14px_14px] text-[13px] leading-[1.7] shadow-[0_1px_4px_rgba(0,0,0,0.04)]">
                    <AIMarkdown text={currentStreamText} />
                  </div>
                </div>
              )
            })()}

            {/* Typing dots + slow-response warning */}
            {isStreaming && !currentStreamText && (
              <div className="mb-4 message-enter">
                <div className="flex items-center gap-2 mb-1.5">
                  <div className="w-6 h-6 rounded-lg bg-[#8A7E6B] flex items-center justify-center text-white">
                    <Compass className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-[12px] font-semibold text-[#8A7E6B]">思考中</span>
                </div>
                <div className="flex gap-[5px] px-4 py-3 bg-white/80 border border-[rgba(107,62,46,0.12)]/50 rounded-[4px_14px_14px_14px] w-fit">
                  <div className="typing-dot bg-slate-400" />
                  <div className="typing-dot bg-slate-400" />
                  <div className="typing-dot bg-slate-400" />
                </div>
                {/* Show slow-response hint after 15s */}
                <SlowResponseHint isStreaming={isStreaming} />
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Input ── */}
      <div className="px-3 pb-3 pt-2 border-t border-black/[0.06]">
        <div className="relative glass-static !rounded-xl !border-white/50 p-2 flex flex-col focus-within:!border-[var(--chestnut)]/30 focus-within:shadow-[0_0_0_2px_rgba(37,99,235,0.1)]">
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputText}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={placeholders[placeholderIdx]}
            className={`
              w-full bg-transparent border-none outline-none resize-none
              text-[#1F1F1F] placeholder:text-[#A89B8C]
              px-2 py-2 min-h-[40px] max-h-[100px] text-[13px] leading-relaxed
              placeholder:transition-opacity placeholder:duration-250
              ${placeholderFading ? 'placeholder:opacity-0' : 'placeholder:opacity-100'}
            `}
          />
          <div className="flex items-center justify-end px-1">
            <button
              onClick={handleSend}
              disabled={!hasText}
              className={`
                w-7 h-7 flex items-center justify-center rounded-lg
                transition-all duration-150 disabled:cursor-not-allowed
                active:scale-[0.92]
                ${hasText
                  ? 'bg-[var(--chestnut)]/[0.12] text-[var(--chestnut)] border border-[var(--chestnut)]/30 hover:bg-[var(--chestnut)]/[0.20]'
                  : 'bg-white/40 text-[var(--text-3)] border border-white/40'
                }
              `}
            >
              <ArrowUp className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Compact message bubble for panel ── */
/* ── Result type labels ── */
/* ── Agent role display config ── */
const agentConfig: Record<string, { name: string; color: string }> = {
  coach_agent:    { name: '智析教练', color: 'bg-[var(--chestnut)]' },
  navigator:      { name: '方向顾问', color: 'bg-[#8A7E6B]' },
  jd_agent:       { name: '匹配分析师', color: 'bg-[#8A7E6B]' },
  profile_agent:  { name: '画像顾问', color: 'bg-[#8A7E6B]' },
  growth_agent:   { name: '成长顾问', color: 'bg-[#8A7E6B]' },
  report_agent:   { name: '报告分析师', color: 'bg-[#8A7E6B]' },
}

const resultTypeLabel: Record<string, string> = {
  jd_diagnosis: 'JD 诊断',
  career_report: '职业报告',
  growth_analysis: '成长分析',
  interview_review: '面试复盘',
  career_exploration: '方向探索',
  profile_analysis: '画像分析',
  general: '分析结果',
}

/* ── Action Card for long results ── */
function ActionCard({ card, onClick }: { card: CardData; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full mt-2 p-3 rounded-xl glass-static text-left cursor-pointer group hover:border-white/60 hover:shadow-sm transition-all"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-[var(--chestnut)] bg-[var(--chestnut)]/10 px-2 py-0.5 rounded-full">
            {resultTypeLabel[card.type] ?? card.type}
          </span>
          <span className="text-[12px] font-medium text-[#3D352E] truncate max-w-[200px]">
            {card.title}
          </span>
        </div>
        <span className="text-[12px] font-semibold text-[var(--chestnut)] group-hover:translate-x-0.5 transition-transform">
          查看 →
        </span>
      </div>
    </button>
  )
}

/* ── Market Signal Cards ── */
function MarketCards({ cards }: { cards: MarketCardData[] }) {
  const navigate = useNavigate()

  const cfg: Record<string, { icon: string; border: string; bg: string; badge: string; text: string }> = {
    best:    { icon: '✅', border: 'border-[rgba(107,62,46,0.12)]', bg: 'bg-white/60', badge: 'bg-white/80 text-[#6B5E4F]', text: 'text-[#8A7E6B]' },
    good:    { icon: '✓',  border: 'border-[rgba(107,62,46,0.12)]', bg: 'bg-white/60', badge: 'bg-white/80 text-[#6B5E4F]', text: 'text-[#8A7E6B]' },
    neutral: { icon: '→',  border: 'border-[rgba(107,62,46,0.12)]', bg: 'bg-white/60', badge: 'bg-white/80 text-[#6B5E4F]', text: 'text-[#8A7E6B]' },
    caution: { icon: '⚠️', border: 'border-[rgba(107,62,46,0.12)]', bg: 'bg-white/60', badge: 'bg-white/80 text-[#6B5E4F]', text: 'text-[#8A7E6B]' },
    no_data: { icon: '—',  border: 'border-[rgba(107,62,46,0.12)]', bg: 'bg-white/60', badge: 'bg-white/80 text-[#8A7E6B]', text: 'text-[#A89B8C]' },
  }

  return (
    <div className="mt-3 pt-3 border-t border-[rgba(107,62,46,0.08)]">
      <div className="text-[10px] text-[#A89B8C] mb-2 flex items-center gap-1">
        <span>系统市场数据</span>
        <span>·</span>
        <span>2021→2024 年真实招聘趋势</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {cards.map(card => {
          const c = cfg[card.timing] ?? cfg.neutral
          const demandSign = card.demand_change_pct >= 0 ? '▲' : '▼'
          const salarySign = card.salary_cagr >= 0 ? '+' : ''
          return (
            <div
              key={card.family}
              className={`flex-1 min-w-[130px] max-w-[180px] rounded-lg border ${c.border} ${c.bg} p-2.5 ${card.node_id ? 'cursor-pointer hover:shadow-sm' : ''} transition-shadow`}
              onClick={() => card.node_id && navigate(`/roles/${encodeURIComponent(card.node_id)}`)}
            >
              <div className="flex items-start justify-between gap-1 mb-2">
                <span className="font-medium text-xs text-[#3D352E] leading-tight">{card.family}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${c.badge}`}>{c.icon}</span>
              </div>
              <div className="space-y-1">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-[#A89B8C]">市场需求</span>
                  <span className={`font-medium ${card.demand_change_pct >= 0 ? 'text-[var(--chestnut)]' : 'text-red-500'}`}>
                    {demandSign} {Math.abs(card.demand_change_pct).toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-[#A89B8C]">薪资趋势</span>
                  <span className={`font-medium ${card.salary_cagr >= 3 ? 'text-[var(--chestnut)]' : card.salary_cagr >= 0 ? 'text-[#8A7E6B]' : 'text-red-500'}`}>
                    {salarySign}{card.salary_cagr.toFixed(0)}%/年
                  </span>
                </div>
              </div>
              {card.role_examples && card.role_examples.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {card.role_examples.map(r => (
                    <span key={r} className="text-[9px] px-1 py-0.5 bg-white/70 rounded text-[#8A7E6B] border border-[rgba(107,62,46,0.12)]">{r}</span>
                  ))}
                </div>
              )}
              {card.node_id && (
                <div className="mt-1.5 text-[10px] text-[#A89B8C]">查看详情 →</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ── JD Search Result Cards ── */
function JdSearchCards({ cards, onDiagnose }: { cards: JdCardData[]; onDiagnose: (jd: JdCardData) => void }) {
  const [expandedIdx, setExpandedIdx] = useState<string | null>(null)

  return (
    <div className="mt-2 space-y-2">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[#8A7E6B] mb-1">
        <Search className="w-3 h-3" />
        搜到 {cards.length} 份招聘
      </div>
      {cards.map((jd) => (
        <div
          key={jd.url}
          className="p-3 rounded-xl bg-white/50 border border-[rgba(107,62,46,0.12)]/60 hover:border-slate-300 transition-all"
        >
          <span className="text-[13px] font-semibold text-[#1F1F1F] leading-tight line-clamp-2 block mb-1">
            {jd.title}
          </span>
          <p className="text-[11px] text-[#A89B8C] mb-2">来源：{jd.source}</p>
          {jd.skills.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {jd.skills.map((s) => (
                <span key={s} className="px-1.5 py-0.5 rounded text-[10px] font-medium text-[#6B5E4F] bg-[#F2EDE4]">
                  {s}
                </span>
              ))}
            </div>
          )}
          {/* JD content preview */}
          {jd.requirements && (
            <div className="mb-2">
              <p className={`text-[11px] text-[#8A7E6B] leading-relaxed whitespace-pre-line ${expandedIdx === jd.url ? '' : 'line-clamp-3'}`}>
                {jd.requirements}
              </p>
              {jd.requirements.length > 100 && (
                <button
                  onClick={() => setExpandedIdx(expandedIdx === jd.url ? null : jd.url)}
                  className="text-[11px] text-[var(--chestnut)] font-medium mt-0.5 cursor-pointer"
                >
                  {expandedIdx === jd.url ? '收起' : '展开全部'}
                </button>
              )}
            </div>
          )}
          <button
            onClick={() => onDiagnose(jd)}
            className="w-full py-1.5 rounded-lg text-[12px] font-semibold text-[var(--chestnut)] bg-white/60 hover:bg-white/80 border border-white/50 transition-colors cursor-pointer"
          >
            诊断匹配度
          </button>
        </div>
      ))}
    </div>
  )
}


/* ── Slow Response Hint ── */
function SlowResponseHint({ isStreaming }: { isStreaming: boolean }) {
  const [show, setShow] = useState(false)
  useEffect(() => {
    if (!isStreaming) { setShow(false); return }
    const t = setTimeout(() => setShow(true), 15000)
    return () => clearTimeout(t)
  }, [isStreaming])
  if (!show) return null
  return (
    <p className="text-[10px] text-[#A89B8C] mt-1.5 ml-1">
      AI 正在思考中，复杂任务可能需要 30 秒...
    </p>
  )
}

/* ── Add to Tracking Button ── */
function AddToTrackingButton({ card }: { card: CardData }) {
  const [state, setState] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const navigate = useNavigate()

  function parseJdTitle(title: string): { company: string; position: string } {
    const separators = /[—\-·|]/
    const parts = title.split(separators).map(s => s.trim()).filter(Boolean)
    if (parts.length >= 2) {
      return { company: parts[0], position: parts.slice(1).join(' ') }
    }
    return { company: '', position: title }
  }

  async function handleAdd() {
    if (state !== 'idle') return
    setState('loading')
    try {
      // Priority: card.company + card.jd_title > parsed title fallback
      let company = card.company || ''
      let position = card.jd_title || ''
      if (!company && !position) {
        const parsed = parseJdTitle(card.title || '')
        company = parsed.company
        position = parsed.position
      } else if (!position) {
        // Have company from LLM but no explicit position, fall back to title
        position = card.title || ''
      }
      await createApplication({
        company: company || undefined,
        position: position || undefined,
        job_url: card.job_url || undefined,
      })
      setState('done')
    } catch {
      setState('error')
      setTimeout(() => setState('idle'), 2000)
    }
  }

  if (state === 'done') {
    return (
      <button
        onClick={() => {
          setState('idle')        // 重置，允许删掉后再次添加
          navigate('/growth-log?tab=pursuits')
        }}
        className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium text-[#6B5E4F] bg-white/60 hover:bg-white/80 border border-white/50 hover:border-white/70 transition-colors cursor-pointer"
        title="前往成长档案 · 返回后可重新添加"
      >
        <CheckCircle2 className="w-3 h-3" /> 已加入追踪 →
      </button>
    )
  }

  return (
    <button
      onClick={handleAdd}
      disabled={state === 'loading'}
      className="px-2.5 py-1 rounded-lg text-[11px] font-medium text-[#6B5E4F] bg-white/60 hover:bg-white/80 border border-white/50 transition-colors cursor-pointer disabled:opacity-60"
    >
      {state === 'loading' ? '添加中...' : state === 'error' ? '添加失败，重试' : '+ 加入实战追踪'}
    </button>
  )
}

function PanelBubble({
  message,
  onTTSToggle,
  isTTSPlaying,
  onCardClick,
  onJdDiagnose,
  onFollowUp,
}: {
  message: ChatMessage
  onTTSToggle?: (id: string, text: string) => void
  isTTSPlaying?: boolean
  onCardClick?: (card: CardData) => void
  onJdDiagnose?: (jd: JdCardData) => void
  onFollowUp?: (text: string) => void
}) {
  if (message.role === 'user') {
    // System notifications (sent internally, not by user) — show as subtle divider, not a bubble
    if (message.text.startsWith('[系统通知]')) {
      const summary = message.text.replace(/^\[系统通知\]\s*/, '').split('。')[0]
      return (
        <div className="mb-3 flex items-center gap-2 px-1">
          <div className="flex-1 h-px bg-[#F2EDE4]" />
          <span className="text-[10px] text-[#C4B8A8] shrink-0">{summary}</span>
          <div className="flex-1 h-px bg-[#F2EDE4]" />
        </div>
      )
    }
    return (
      <div className="mb-4 flex justify-end message-enter">
        <div className="bg-[var(--chestnut)]/[0.12] border border-[var(--chestnut)]/30 text-[var(--chestnut)] px-4 py-2.5 rounded-[14px_14px_4px_14px] max-w-[85%] text-[13px] leading-[1.6]">
          {message.text}
        </div>
      </div>
    )
  }

  const agentCfg = agentConfig[message.agent ?? ''] ?? agentConfig.coach_agent

  return (
    <div className="mb-4 group message-enter">
      <div className="flex items-center gap-2 mb-1.5">
        <div className={`w-6 h-6 rounded-lg ${agentCfg.color} flex items-center justify-center text-white`}>
          <Compass className="w-3.5 h-3.5" />
        </div>
        <span className="text-[12px] font-semibold text-[#8A7E6B]">{agentCfg.name}</span>
        {onTTSToggle && (
          <button
            onClick={() => onTTSToggle(message.id, message.text)}
            className={`ml-auto p-1 rounded transition-all cursor-pointer ${
              isTTSPlaying
                ? 'text-[#8A7E6B] bg-white/60'
                : 'text-[#C4B8A8] hover:text-[#8A7E6B] opacity-0 group-hover:opacity-100 focus-visible:opacity-100'
            }`}
            title={isTTSPlaying ? '停止朗读' : '朗读'}
            aria-label={isTTSPlaying ? '停止朗读' : '朗读'}
          >
            {isTTSPlaying ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
          </button>
        )}
      </div>
      <div className="bg-white/80 border border-[rgba(107,62,46,0.12)]/50 text-[var(--text-1)] px-4 py-3 rounded-[4px_14px_14px_14px] max-w-[95%] text-[13px] leading-[1.7] shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
        <AIMarkdown text={message.text} />
      </div>
      {message.card && onCardClick && (
        <ActionCard card={message.card} onClick={() => onCardClick(message.card!)} />
      )}
      {message.jdCards && message.jdCards.length > 0 && onJdDiagnose && (
        <JdSearchCards cards={message.jdCards} onDiagnose={onJdDiagnose} />
      )}
      {message.marketCards && message.marketCards.length > 0 && (
        <MarketCards cards={message.marketCards} />
      )}
      {/* Follow-up chips after JD diagnosis */}
      {message.card?.type === 'jd_diagnosis' && onFollowUp && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {[
            { label: '练缺口面试题', prompt: '根据上次JD诊断的缺口技能，帮我出几道相关面试题练练' },
            { label: '搜类似岗位', prompt: '帮我搜索和刚才诊断的JD类似的其他招聘' },
            { label: '制定学习计划', prompt: '根据刚才的诊断缺口，帮我制定一个补强计划' },
          ].map((chip) => (
            <button
              key={chip.label}
              onClick={() => onFollowUp(chip.prompt)}
              className="px-2.5 py-1 rounded-lg text-[11px] font-medium text-[#6B5E4F] bg-white/50 hover:bg-white/70 border border-white/40 transition-colors cursor-pointer"
            >
              {chip.label}
            </button>
          ))}
          <AddToTrackingButton card={message.card} />
        </div>
      )}
    </div>
  )
}
