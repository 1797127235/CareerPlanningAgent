import { useState } from 'react'

interface TagChipsProps {
  tags: string[]
  onChange: (tags: string[]) => void
}

const PRESETS = ['项目', '面试', '学习']

export function TagChips({ tags, onChange }: TagChipsProps) {
  const [showInput, setShowInput] = useState(false)
  const [inputValue, setInputValue] = useState('')

  const togglePreset = (preset: string) => {
    if (tags.includes(preset)) {
      onChange(tags.filter((t) => t !== preset))
    } else {
      // 预设标签互斥——选择新的 preset 时清掉已选的其他 presets，保留用户自定义标签
      const withoutOtherPresets = tags.filter((t) => !PRESETS.includes(t))
      onChange([...withoutOtherPresets, preset])
    }
  }

  const addCustom = () => {
    const v = inputValue.trim()
    if (v && !tags.includes(v)) {
      onChange([...tags, v])
    }
    setInputValue('')
    setShowInput(false)
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {PRESETS.map((preset) => {
        const active = tags.includes(preset)
        return (
          <button
            key={preset}
            onClick={() => togglePreset(preset)}
            className={[
              'px-2.5 py-1 rounded-full text-[11px] font-semibold tracking-wide transition-colors cursor-pointer',
              active
                ? 'bg-blue-600 text-white'
                : 'bg-slate-100 text-slate-500 hover:bg-slate-200',
            ].join(' ')}
          >
            #{preset}
          </button>
        )
      })}

      {showInput ? (
        <input
          autoFocus
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') addCustom()
            if (e.key === 'Escape') {
              setShowInput(false)
              setInputValue('')
            }
          }}
          onBlur={() => {
            if (inputValue.trim()) addCustom()
            else setShowInput(false)
          }}
          className="w-24 px-2 py-1 text-[11px] border border-slate-300 rounded-full outline-none focus:border-blue-500"
          placeholder="回车添加"
        />
      ) : (
        <button
          onClick={() => setShowInput(true)}
          className="px-2.5 py-1 rounded-full text-[11px] font-semibold tracking-wide bg-slate-50 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors cursor-pointer"
        >
          +自定义
        </button>
      )}

      {tags
        .filter((t) => !PRESETS.includes(t))
        .map((t) => (
          <span
            key={t}
            className="px-2.5 py-1 rounded-full text-[11px] font-semibold tracking-wide bg-blue-600 text-white flex items-center gap-1"
          >
            #{t}
            <button
              onClick={() => onChange(tags.filter((x) => x !== t))}
              className="ml-0.5 text-white/80 hover:text-white cursor-pointer"
            >
              ×
            </button>
          </span>
        ))}
    </div>
  )
}
