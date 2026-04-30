import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import type { V2ProfileData } from '@/types/profile-v2'

interface Props {
  open: boolean
  onClose: () => void
  initialData: V2ProfileData
  onSave: (patch: Partial<V2ProfileData>) => Promise<void>
}

const CITY_OPTIONS = ['北京', '上海', '深圳', '杭州', '广州', '成都', '远程']
const INDUSTRY_OPTIONS = ['互联网', 'AI/ML', '金融科技', '企业服务', '游戏', '新能源']
const COMPANY_OPTIONS = ['大厂', '独角兽', '外企', '国企', '初创']
const GROWTH_OPTIONS = [
  { value: 'fast', label: '快速晋升' },
  { value: 'steady', label: '稳健成长' },
  { value: 'balance', label: 'Work-life balance' },
]

const MODAL_BACKDROP = { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: { duration: 0.15 } }
const MODAL_CARD = {
  initial: { opacity: 0, scale: 0.96, y: 8 },
  animate: { opacity: 1, scale: 1, y: 0 },
  exit: { opacity: 0, scale: 0.96, y: 8 },
  transition: { duration: 0.2, ease: [0.22, 1, 0.36, 1] },
}

export default function ProfileEditForm({ open, onClose, initialData, onSave }: Props) {
  const [tags, setTags] = useState(initialData.tags?.join(', ') ?? '')
  const [strengths, setStrengths] = useState(initialData.strengths?.join('\n') ?? '')
  const [weaknesses, setWeaknesses] = useState(initialData.weaknesses?.join('\n') ?? '')
  const [cities, setCities] = useState<string[]>(
    initialData.constraints?.filter((c) => c.type === 'location').map((c) => c.value) ?? []
  )
  const [industries, setIndustries] = useState<string[]>(
    initialData.preferences?.filter((p) => p.type === 'industry').map((p) => p.value) ?? []
  )
  const [companySizes, setCompanySizes] = useState<string[]>(
    initialData.preferences?.filter((p) => p.type === 'company_size').map((p) => p.value) ?? []
  )
  const [growth, setGrowth] = useState(
    initialData.preferences?.find((p) => p.type === 'growth_speed')?.value ?? ''
  )
  const [salary, setSalary] = useState(
    initialData.constraints?.find((c) => c.type === 'salary_min')?.value ?? ''
  )
  const [saving, setSaving] = useState(false)

  const prevOpenRef = useRef(false)
  useEffect(() => {
    if (open && !prevOpenRef.current) {
      setTags(initialData.tags?.join(', ') ?? '')
      setStrengths(initialData.strengths?.join('\n') ?? '')
      setWeaknesses(initialData.weaknesses?.join('\n') ?? '')
      setCities(initialData.constraints?.filter((c) => c.type === 'location').map((c) => c.value) ?? [])
      setIndustries(initialData.preferences?.filter((p) => p.type === 'industry').map((p) => p.value) ?? [])
      setCompanySizes(initialData.preferences?.filter((p) => p.type === 'company_size').map((p) => p.value) ?? [])
      setGrowth(initialData.preferences?.find((p) => p.type === 'growth_speed')?.value ?? '')
      setSalary(initialData.constraints?.find((c) => c.type === 'salary_min')?.value ?? '')
    }
    prevOpenRef.current = open
  }, [open, initialData])

  const handleSubmit = async () => {
    setSaving(true)
    try {
      const patch: Partial<V2ProfileData> = {
        tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
        strengths: strengths.split('\n').map((s) => s.trim()).filter(Boolean),
        weaknesses: weaknesses.split('\n').map((w) => w.trim()).filter(Boolean),
        constraints: [
          ...cities.map((c) => ({ type: 'location' as const, value: c, label: c })),
          ...(salary ? [{ type: 'salary_min' as const, value: salary, label: `${salary}元/月` }] : []),
        ],
        preferences: [
          ...industries.map((i) => ({ type: 'industry' as const, value: i, label: i })),
          ...companySizes.map((c) => ({ type: 'company_size' as const, value: c, label: c })),
          ...(growth ? [{ type: 'growth_speed' as const, value: growth, label: GROWTH_OPTIONS.find((g) => g.value === growth)?.label ?? growth }] : []),
        ],
      }
      await onSave(patch)
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          {...MODAL_BACKDROP}
          className="fixed inset-0 bg-[var(--ink-1)]/20 backdrop-blur-sm z-[999] flex items-center justify-center p-6"
          onClick={onClose}
        >
          <motion.div
            {...MODAL_CARD}
            className="bg-[var(--bg-card)] rounded-[var(--radius-lg)] shadow-[var(--shadow-float)] p-6 max-w-lg w-full border border-[var(--line)] max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-[var(--text-xl)] font-semibold text-[var(--ink-1)]">补充画像信息</h3>
              <button onClick={onClose} className="text-[var(--ink-3)] hover:text-[var(--ink-1)] transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-5">
              {/* Tags */}
              <div>
                <label className="block text-[13px] font-medium mb-1.5" style={{ color: 'var(--ink-2)' }}>标签（逗号分隔）</label>
                <input
                  className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--bg-paper)] border border-[var(--line)] text-[var(--ink-1)] text-[13px] focus:outline-none focus:border-[var(--chestnut)]/50 transition-[border-color] duration-200"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="Python, 后端, 应届生"
                />
              </div>

              {/* Strengths */}
              <div>
                <label className="block text-[13px] font-medium mb-1.5" style={{ color: 'var(--ink-2)' }}>
                  自我评价优势 <span className="text-[11px] font-normal" style={{ color: 'var(--ink-3)' }}>(每行一条，{strengths.length}/500字)</span>
                </label>
                <textarea
                  className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--bg-paper)] border border-[var(--line)] text-[var(--ink-1)] text-[13px] focus:outline-none focus:border-[var(--chestnut)]/50 transition-[border-color] duration-200 h-20 resize-none"
                  value={strengths}
                  onChange={(e) => { if (e.target.value.length <= 500) setStrengths(e.target.value) }}
                  placeholder="算法基础扎实&#10;有实习经历"
                />
              </div>

              {/* Weaknesses */}
              <div>
                <label className="block text-[13px] font-medium mb-1.5" style={{ color: 'var(--ink-2)' }}>
                  自我评价短板 <span className="text-[11px] font-normal" style={{ color: 'var(--ink-3)' }}>(每行一条，{weaknesses.length}/500字)</span>
                </label>
                <textarea
                  className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--bg-paper)] border border-[var(--line)] text-[var(--ink-1)] text-[13px] focus:outline-none focus:border-[var(--chestnut)]/50 transition-[border-color] duration-200 h-20 resize-none"
                  value={weaknesses}
                  onChange={(e) => { if (e.target.value.length <= 500) setWeaknesses(e.target.value) }}
                  placeholder="无大规模系统经验&#10;缺少海外背景"
                />
              </div>

              {/* Cities */}
              <div>
                <label className="block text-[13px] font-medium mb-2" style={{ color: 'var(--ink-2)' }}>期望工作城市</label>
                <div className="flex flex-wrap gap-2">
                  {CITY_OPTIONS.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setCities((prev) => prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c])}
                      className={`px-3 py-1.5 rounded-full text-[12px] font-medium border transition-colors cursor-pointer ${
                        cities.includes(c)
                          ? 'bg-[var(--chestnut)] text-white border-[var(--chestnut)]'
                          : 'bg-[var(--bg-paper)] text-[var(--ink-2)] border-[var(--line)] hover:border-[var(--chestnut)]/50'
                      }`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>

              {/* Industries */}
              <div>
                <label className="block text-[13px] font-medium mb-2" style={{ color: 'var(--ink-2)' }}>感兴趣的行业</label>
                <div className="flex flex-wrap gap-2">
                  {INDUSTRY_OPTIONS.map((i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setIndustries((prev) => prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i])}
                      className={`px-3 py-1.5 rounded-full text-[12px] font-medium border transition-colors cursor-pointer ${
                        industries.includes(i)
                          ? 'bg-[var(--chestnut)] text-white border-[var(--chestnut)]'
                          : 'bg-[var(--bg-paper)] text-[var(--ink-2)] border-[var(--line)] hover:border-[var(--chestnut)]/50'
                      }`}
                    >
                      {i}
                    </button>
                  ))}
                </div>
              </div>

              {/* Company sizes */}
              <div>
                <label className="block text-[13px] font-medium mb-2" style={{ color: 'var(--ink-2)' }}>公司规模偏好</label>
                <div className="flex flex-wrap gap-2">
                  {COMPANY_OPTIONS.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setCompanySizes((prev) => prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c])}
                      className={`px-3 py-1.5 rounded-full text-[12px] font-medium border transition-colors cursor-pointer ${
                        companySizes.includes(c)
                          ? 'bg-[var(--chestnut)] text-white border-[var(--chestnut)]'
                          : 'bg-[var(--bg-paper)] text-[var(--ink-2)] border-[var(--line)] hover:border-[var(--chestnut)]/50'
                      }`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>

              {/* Growth speed */}
              <div>
                <label className="block text-[13px] font-medium mb-1.5" style={{ color: 'var(--ink-2)' }}>成长速度偏好</label>
                <select
                  className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--bg-paper)] border border-[var(--line)] text-[var(--ink-1)] text-[13px] focus:outline-none focus:border-[var(--chestnut)]/50 transition-[border-color] duration-200"
                  value={growth}
                  onChange={(e) => setGrowth(e.target.value)}
                >
                  <option value="">请选择</option>
                  {GROWTH_OPTIONS.map((g) => (
                    <option key={g.value} value={g.value}>{g.label}</option>
                  ))}
                </select>
              </div>

              {/* Salary */}
              <div>
                <label className="block text-[13px] font-medium mb-1.5" style={{ color: 'var(--ink-2)' }}>
                  最低薪资期望 <span className="text-[11px] font-normal" style={{ color: 'var(--ink-3)' }}>(元/月，可选)</span>
                </label>
                <input
                  type="number"
                  min={0}
                  className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--bg-paper)] border border-[var(--line)] text-[var(--ink-1)] text-[13px] focus:outline-none focus:border-[var(--chestnut)]/50 transition-[border-color] duration-200"
                  value={salary}
                  onChange={(e) => setSalary(e.target.value)}
                  placeholder="15000"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 mt-6 pt-4 border-t border-[var(--line)]">
              <button
                onClick={onClose}
                className="flex-[2] py-2.5 rounded-full text-[13px] font-medium border border-[var(--line)] text-[var(--ink-1)] hover:bg-[var(--line)]/10 transition-colors active:scale-[0.98]"
              >
                取消
              </button>
              <button
                onClick={handleSubmit}
                disabled={saving}
                className="flex-1 py-2.5 rounded-full text-[13px] font-medium bg-[var(--chestnut)] text-white hover:opacity-90 transition-opacity active:scale-[0.98] disabled:opacity-50"
              >
                {saving ? '保存中…' : '保存'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
