/**
 * Coach trigger event system.
 *
 * Pages dispatch trigger events after key actions (profile update, goal set, etc.).
 * ChatPanel listens and auto-sends a system message to the coach.
 */
import { useEffect, useCallback } from 'react'

export type TriggerType =
  | 'goal-set'
  | 'resume-uploaded'

interface CoachTriggerDetail {
  type: TriggerType
  context: string // e.g., "技能数量: 12" or "目标: 前端工程师"
}

const EVENT_NAME = 'coach-trigger'

/** Dispatch a trigger event from any page */
export function dispatchCoachTrigger(type: TriggerType, context: string) {
  window.dispatchEvent(
    new CustomEvent<CoachTriggerDetail>(EVENT_NAME, {
      detail: { type, context },
    }),
  )
}

/** System messages sent to the coach for each trigger type */
const triggerMessages: Record<TriggerType, (ctx: string) => string> = {
  'goal-set': (ctx) => `[系统通知] 用户刚设定了职业目标：${ctx}。请给出鼓励和具体的下一步行动建议。`,
  'resume-uploaded': (ctx) => `[系统通知] ${ctx}`,
}

/** Send a direct prompt to the coach panel (from any page) */
export function sendToCoach(prompt: string) {
  window.dispatchEvent(new CustomEvent('coach-send', { detail: prompt }))
}

export function useCoachTriggerListener(
  sendMessage: (text: string) => void,
  isStreaming: boolean,
) {
  const handler = useCallback(
    (e: Event) => {
      const { type, context } = (e as CustomEvent<CoachTriggerDetail>).detail
      if (isStreaming) return // Don't interrupt ongoing stream
      const msgFn = triggerMessages[type]
      if (msgFn) sendMessage(msgFn(context))
    },
    [sendMessage, isStreaming],
  )

  // Listen for coach trigger events
  useEffect(() => {
    window.addEventListener(EVENT_NAME, handler)
    return () => window.removeEventListener(EVENT_NAME, handler)
  }, [handler])

  // Listen for direct coach-send events (from CoachResultPage etc.)
  useEffect(() => {
    const sendHandler = (e: Event) => {
      const prompt = (e as CustomEvent<string>).detail
      if (prompt && !isStreaming) sendMessage(prompt)
    }
    window.addEventListener('coach-send', sendHandler)
    return () => window.removeEventListener('coach-send', sendHandler)
  }, [sendMessage, isStreaming])
}
