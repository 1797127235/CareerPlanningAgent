/**
 * 项目图节点组件
 * 双击标题可内联编辑，点击状态圆点循环切换状态
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { Handle, Position } from '@xyflow/react'
import type { NodeStatus } from '@/pages/ProjectGraphPage'
import { STATUS_COLOR, STATUS_LABEL } from '@/pages/ProjectGraphPage'

interface ProjectNodeData {
  label: string
  status: NodeStatus
  onUpdate?: (id: string, data: Partial<{ label: string; status: NodeStatus }>) => void
}

const STATUS_CYCLE: NodeStatus[] = ['todo', 'in_progress', 'done']

export function ProjectNode({ id, data, selected }: {
  id: string
  data: ProjectNodeData
  selected?: boolean
}) {
  const { label, status, onUpdate } = data
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(label)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editing])

  const commitEdit = useCallback(() => {
    setEditing(false)
    const trimmed = draft.trim() || label
    setDraft(trimmed)
    if (trimmed !== label) onUpdate?.(id, { label: trimmed })
  }, [draft, label, id, onUpdate])

  const cycleStatus = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    const next = STATUS_CYCLE[(STATUS_CYCLE.indexOf(status) + 1) % STATUS_CYCLE.length]
    onUpdate?.(id, { status: next })
  }, [status, id, onUpdate])

  const color = STATUS_COLOR[status]

  return (
    <div
      className="relative"
      style={{
        minWidth: 140,
        maxWidth: 200,
      }}
    >
      {/* Connection handles */}
      <Handle type="target" position={Position.Top} style={{ background: '#CBD5E1', width: 8, height: 8, border: '2px solid white' }} />
      <Handle type="source" position={Position.Bottom} style={{ background: '#CBD5E1', width: 8, height: 8, border: '2px solid white' }} />
      <Handle type="target" position={Position.Left} style={{ background: '#CBD5E1', width: 8, height: 8, border: '2px solid white' }} />
      <Handle type="source" position={Position.Right} style={{ background: '#CBD5E1', width: 8, height: 8, border: '2px solid white' }} />

      {/* Node card */}
      <div
        style={{
          background: 'rgba(255,255,255,0.85)',
          backdropFilter: 'blur(12px)',
          border: selected ? `2px solid ${color}` : '1.5px solid rgba(255,255,255,0.6)',
          borderRadius: 12,
          boxShadow: selected
            ? `0 0 0 3px ${color}22, 0 4px 16px rgba(0,0,0,0.10)`
            : '0 2px 8px rgba(0,0,0,0.08)',
          padding: '8px 12px',
          transition: 'box-shadow 0.15s, border-color 0.15s',
        }}
      >
        {/* Status dot + label */}
        <div className="flex items-center gap-2">
          <button
            onClick={cycleStatus}
            title={STATUS_LABEL[status]}
            className="shrink-0 cursor-pointer"
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: color,
              border: '1.5px solid white',
              boxShadow: `0 0 0 1.5px ${color}`,
              transition: 'background 0.2s',
            }}
          />

          {editing ? (
            <input
              ref={inputRef}
              value={draft}
              onChange={e => setDraft(e.target.value)}
              onBlur={commitEdit}
              onKeyDown={e => {
                if (e.key === 'Enter') commitEdit()
                if (e.key === 'Escape') { setEditing(false); setDraft(label) }
              }}
              className="flex-1 text-[12px] font-semibold text-slate-800 outline-none bg-transparent border-b border-blue-400 min-w-0"
              style={{ minWidth: 80 }}
            />
          ) : (
            <span
              onDoubleClick={(e) => { e.stopPropagation(); setEditing(true); setDraft(label) }}
              className="flex-1 text-[12px] font-semibold text-slate-800 select-none truncate cursor-text"
              title={label}
            >
              {label}
            </span>
          )}
        </div>

        {/* Status badge */}
        <div className="mt-1.5 ml-4">
          <span
            className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full"
            style={{ background: `${color}18`, color }}
          >
            {STATUS_LABEL[status]}
          </span>
        </div>
      </div>
    </div>
  )
}
