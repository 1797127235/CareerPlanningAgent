import { motion } from 'framer-motion'
import { X, FolderGit2, Briefcase } from 'lucide-react'
import type { RecordType } from './RecordRow'

export function NewRecordDialog({
  onClose,
  onSelect
}: {
  onClose: () => void
  onSelect: (type: RecordType) => void
}) {
  const options: { type: RecordType, icon: any, color: string, title: string, desc: string }[] = [
    {
      type: 'project',
      icon: FolderGit2,
      color: '#EA580C',
      title: '记录项目',
      desc: '记录一个正在做或已完成的项目',
    },
    {
      type: 'pursuit',
      icon: Briefcase,
      color: 'var(--ember)',
      title: '追踪岗位',
      desc: '记录投递的公司和岗位进展',
    },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div className="absolute inset-0" style={{ background: 'rgba(0,0,0,0.35)' }}
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
      
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        className="relative w-full max-w-[400px] bg-white rounded-2xl overflow-hidden shadow-xl"
      >
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-[15px] font-bold text-slate-800">添加新记录</h3>
          <button onClick={onClose} className="p-1.5 hover:bg-slate-100 rounded-full transition-colors">
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        <div className="p-3 space-y-1.5 bg-slate-50/50">
          {options.map(opt => (
            <button
              key={opt.type}
              onClick={() => onSelect(opt.type)}
              className="w-full flex items-center gap-3 p-3 rounded-xl bg-white border border-slate-100 hover:border-slate-300 hover:shadow-sm transition-all text-left group"
            >
              <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 transition-colors"
                style={{ background: `${opt.color}15`, color: opt.color }}>
                <opt.icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[14px] font-bold text-slate-800 group-hover:text-slate-900">{opt.title}</p>
                <p className="text-[12px] text-slate-500 mt-0.5">{opt.desc}</p>
              </div>
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
