/* eslint-disable @typescript-eslint/no-explicit-any */
import type { ProfileData, CheckItem } from '@/types/profile'

/* ── Skill level config ── */
export const levelConfig: Record<string, { label: string; cls: string }> = {
  expert:       { label: '精通', cls: 'bg-slate-800 text-white' },
  advanced:     { label: '精通', cls: 'bg-slate-800 text-white' },
  proficient:   { label: '熟悉', cls: 'bg-slate-600 text-white' },
  intermediate: { label: '熟悉', cls: 'bg-slate-600 text-white' },
  familiar:     { label: '了解', cls: 'bg-slate-100 text-slate-600 border border-slate-200' },
  beginner:     { label: '入门', cls: 'bg-neutral-50 text-neutral-400 border border-neutral-200' },
  entry:        { label: '入门', cls: 'bg-neutral-50 text-neutral-400 border border-neutral-200' },
}

export const levelOrder = ['expert', 'advanced', 'proficient', 'intermediate', 'familiar', 'beginner', 'entry']

/* ── Motion variants ── */
export const cardVariants: any = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.3, ease: [0.23, 1, 0.32, 1], delay: i * 0.06 },
  }),
  hover: {
    y: -3,
    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.08)',
    transition: { duration: 0.2, ease: 'easeOut' },
  },
}

export const tagVariants: any = {
  hidden: { opacity: 0, scale: 0.85 },
  visible: (i: number) => ({
    opacity: 1,
    scale: 1,
    transition: { duration: 0.2, ease: 'easeOut', delay: 0.15 + i * 0.03 },
  }),
}

export const barVariants: any = {
  hidden: { width: 0 },
  visible: (score: number) => ({
    width: `${score}%`,
    transition: { duration: 0.8, ease: [0.23, 1, 0.32, 1], delay: 0.3 },
  }),
}

/* ── Checklist logic ── */
export function buildChecklist(p: ProfileData): CheckItem[] {
  const prof = p.profile
  const qual = p.quality
  return [
    { label: '基础', done: true },
    { label: '技能', done: (prof.skills?.length ?? 0) > 0 },
    { label: '知识', done: (prof.knowledge_areas?.length ?? 0) > 0 },
    { label: '项目', done: Array.isArray((prof as Record<string, unknown>).projects) && ((prof as Record<string, unknown>).projects as unknown[]).length > 0 },
    { label: '软技能', done: (qual.dimensions?.length ?? 0) > 0 },
  ]
}

/* ── Upload step config ── */
export const uploadSteps = [
  { label: '准备上传', icon: '📤' },
  { label: '上传文件', icon: '📤' },
  { label: 'AI 解析简历', icon: '🧠' },
  { label: '生成画像', icon: '✨' },
]

export const uploadTips = [
  '正在提取简历中的技能关键词...',
  '分析项目经历与技术栈的匹配度...',
  '评估技能熟练度等级（入门→精通）...',
  '识别知识领域与能力特征...',
  '计算画像完整度和就业竞争力...',
  '生成三层能力模型（技能/知识/素质）...',
]
