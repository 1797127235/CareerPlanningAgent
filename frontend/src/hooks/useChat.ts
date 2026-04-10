import { useState, useCallback, useRef } from 'react'
import { API_BASE } from '@/api/client'

export interface CardData {
  type: string
  id: number
  title: string
  score?: number
  gap_count?: number
}

export interface JdCardData {
  title: string
  url: string
  source: string
  skills: string[]
  requirements: string
  full_text: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'ai'
  text: string
  agent?: string  // which agent produced this response
  card?: CardData
  jdCards?: JdCardData[]
}

interface UseChatReturn {
  messages: ChatMessage[]
  isStreaming: boolean
  currentStreamText: string
  currentStreamAgent: string | undefined
  sessionId: number | null
  sendMessage: (text: string) => void
  clearMessages: () => void
  loadSession: (id: number) => Promise<void>
  setPageContext: (ctx: PageContext) => void
}

let idCounter = 0
function genId(): string {
  return `msg_${Date.now()}_${++idCounter}`
}

/** Page context sent alongside each chat message */
export interface PageContext {
  route: string
  label: string
  data?: Record<string, unknown>
}

export function useChat(onComplete?: () => void): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentStreamText, setCurrentStreamText] = useState('')
  const [currentStreamAgent, setCurrentStreamAgent] = useState<string | undefined>()
  const [sessionId, setSessionId] = useState<number | null>(null)
  const sessionIdRef = useRef<number | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const pageContextRef = useRef<PageContext | null>(null)

  const updateSessionId = useCallback((id: number | null) => {
    sessionIdRef.current = id
    setSessionId(id)
  }, [])

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || isStreaming) return

      const userMsg: ChatMessage = { id: genId(), role: 'user', text: trimmed }
      setMessages((prev) => [...prev, userMsg])

      const token = localStorage.getItem('token')
      if (!token) {
        const aiMsg: ChatMessage = {
          id: genId(),
          role: 'ai',
          text: '请先登录后再使用 AI 对话功能。',
        }
        setMessages((prev) => [...prev, aiMsg])
        return
      }

      setIsStreaming(true)
      setCurrentStreamText('')

      const controller = new AbortController()
      abortRef.current = controller

      ;(async () => {
        try {
          const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              message: trimmed,
              ...(sessionIdRef.current !== null && { session_id: sessionIdRef.current }),
              ...(pageContextRef.current && { page_context: pageContextRef.current }),
            }),
            signal: controller.signal,
          })

          if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            const errText = (err as { detail?: string }).detail || '请求失败'
            setMessages((prev) => [
              ...prev,
              { id: genId(), role: 'ai', text: `出错了：${errText}` },
            ])
            setIsStreaming(false)
            setCurrentStreamText('')
            return
          }

          const reader = res.body?.getReader()
          if (!reader) throw new Error('No reader')

          const decoder = new TextDecoder()
          let buffer = ''
          let accumulated = ''
          let pendingCard: CardData | undefined
          let pendingJdCards: JdCardData[] | undefined
          let pendingAgent: string | undefined

          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() ?? ''

            for (const line of lines) {
              if (line.startsWith('data:')) {
                const raw = line.slice(5).trim()
                if (!raw || raw === '[DONE]') continue
                try {
                  const parsed = JSON.parse(raw) as { content?: string; session_id?: number; card?: CardData; jd_cards?: JdCardData[]; agent?: string }
                  if (parsed.content) {
                    accumulated += parsed.content
                    setCurrentStreamText(accumulated)
                  }
                  if (parsed.session_id != null) {
                    updateSessionId(parsed.session_id)
                  }
                  if (parsed.agent) {
                    pendingAgent = parsed.agent
                    setCurrentStreamAgent(parsed.agent)
                  }
                  if (parsed.jd_cards) {
                    pendingJdCards = parsed.jd_cards
                  }
                  if (parsed.card) {
                    pendingCard = parsed.card
                  }
                } catch {
                  /* skip unparseable chunks */
                }
              }
            }
          }

          const finalText = accumulated || getFallbackResponse(trimmed)
          setMessages((prev) => [
            ...prev,
            { id: genId(), role: 'ai', text: finalText, agent: pendingAgent, card: pendingCard, jdCards: pendingJdCards },
          ])
        } catch {
          /* Backend unavailable - use fallback */
          setMessages((prev) => [
            ...prev,
            { id: genId(), role: 'ai', text: getFallbackResponse(trimmed) },
          ])
        } finally {
          setIsStreaming(false)
          setCurrentStreamText('')
          setCurrentStreamAgent(undefined)
          abortRef.current = null
          onComplete?.()
        }
      })()
    },
    [isStreaming, updateSessionId],
  )

  const clearMessages = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    setMessages([])
    setIsStreaming(false)
    setCurrentStreamText('')
    updateSessionId(null)
  }, [updateSessionId])

  const loadSession = useCallback(async (id: number) => {
    const token = localStorage.getItem('token')
    if (!token) return
    try {
      const res = await fetch(`${API_BASE}/chat/sessions/${id}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) return
      const data = await res.json() as Array<{ role: string; content: string }>
      const msgs: ChatMessage[] = data.map((m, i) => ({
        id: `msg_${id}_${i}`,
        role: m.role === 'user' ? 'user' : 'ai',
        text: m.content,
      }))
      setMessages(msgs)
      updateSessionId(id)
    } catch {
      /* silently fail */
    }
  }, [updateSessionId])

  const setPageContext = useCallback((ctx: PageContext) => {
    pageContextRef.current = ctx
  }, [])

  return { messages, isStreaming, currentStreamText, currentStreamAgent, sessionId, sendMessage, clearMessages, loadSession, setPageContext }
}

/* ── Fallback responses when backend is unavailable ── */

const fallbackResponses: Record<string, string> = {
  '分析我的能力画像':
    '好的！能力画像分析需要你的简历或项目经历作为输入。你可以直接粘贴简历内容，我会基于三层能力模型（基础技能、专业技能、元能力）为你构建完整的能力画像，并标注优势区域与待提升维度。\n\n请粘贴你的简历或描述你的技术栈和项目经验，我来开始分析。',
  '帮我探索岗位图谱':
    '岗位图谱已加载完毕，当前覆盖 268 个计算机领域岗位节点和 585 条关联边。\n\n你可以告诉我：\n1. 你当前的岗位或目标方向，我帮你定位在图谱中的位置\n2. 想了解某个方向的上下游岗位关系\n3. 探索从当前岗位到目标岗位的转型路径\n\n你想从哪个方向开始？',
  '诊断 JD 匹配度':
    '请粘贴你感兴趣的 JD（职位描述），我会为你做以下分析：\n\n• 技能匹配度评分（基于你的能力画像）\n• 关键技能缺口清单\n• 优先补齐建议\n• 岗位市场定位\n\n直接粘贴 JD 内容即可开始诊断。',
  '开始面试练习':
    '告诉我你想练哪个方向的面试题（如：后端、前端、算法），我直接出题。',
  '前端和后端该怎么选？':
    '前端 vs 后端的选择取决于你的兴趣倾向和长期目标：\n\n**前端方向**适合你如果：\n• 对视觉效果和用户体验有追求\n• 喜欢即时看到代码运行结果\n• 对 React/Vue 等框架感兴趣\n\n**后端方向**适合你如果：\n• 喜欢处理复杂逻辑和数据\n• 对系统架构和性能优化感兴趣\n• 想深入分布式系统和数据库\n\n你目前更偏向哪方面？我可以结合岗位图谱帮你做更详细的分析。',
  '我的岗位有 AI 替代风险吗？':
    '这是个好问题。AI 替代风险因岗位而异，我可以基于最新的市场信号数据帮你评估。\n\n需要你告诉我你当前的岗位名称和主要工作内容，我会从以下维度分析：\n\n1. **自动化替代概率** — 你的核心任务被 AI 取代的可能性\n2. **增强协作机会** — AI 工具如何增强你的生产力\n3. **安全技能锚点** — 你的哪些能力是 AI 难以替代的\n4. **转型建议** — 如果风险较高，推荐的能力升级路径\n\n你的岗位是什么？',
  '帮我规划转型路径':
    '转型路径规划需要明确起点和终点。请告诉我：\n\n1. **当前岗位**：你现在做什么？（如：Java 后端开发）\n2. **目标方向**：你想转向什么？（如：AI 工程师、技术管理）\n3. **时间预期**：你希望多久完成转型？\n\n我会基于岗位图谱中的关联路径，为你生成：\n• 最短技能桥接路径\n• 分阶段学习计划\n• 关键里程碑节点\n• 市场需求匹配度',
  '帮我生成职业分析报告':
    '职业分析报告将为你全方位呈现职业现状和规划建议。报告包含以下章节：\n\n1. 能力画像总览\n2. 岗位定位与市场分析\n3. 技能缺口诊断\n4. AI 时代生存力评估\n5. 发展路径推荐\n6. 行动计划\n\n为了生成报告，我需要你的基本信息。你可以上传简历，或者简单描述你的技术栈、工作年限和目标方向。',
}

function getFallbackResponse(userMsg: string): string {
  if (fallbackResponses[userMsg]) return fallbackResponses[userMsg]
  return '抱歉，暂时连接不上后端服务。请稍后再试，或者检查后端是否已启动。'
}
