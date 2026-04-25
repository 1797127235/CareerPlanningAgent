export type ResultBucket = 'diagnosis' | 'narrative' | 'review' | 'fallback'

export function bucketOf(type: string, isStructured: boolean): ResultBucket {
  if (type === 'jd_diagnosis' && isStructured) return 'diagnosis'
  if (['career_report', 'career_exploration', 'profile_analysis'].includes(type)) return 'narrative'
  if (['growth_analysis', 'interview_review'].includes(type)) return 'review'
  return 'fallback'
}

export function typeLabelOf(type: string): string {
  const map: Record<string, string> = {
    jd_diagnosis: 'JD 诊断',
    career_report: '职业报告',
    career_exploration: '方向探索',
    profile_analysis: '画像分析',
    growth_analysis: '成长分析',
    interview_review: '面试复盘',
    general: '分析结果',
  }
  return map[type] || '分析结果'
}
