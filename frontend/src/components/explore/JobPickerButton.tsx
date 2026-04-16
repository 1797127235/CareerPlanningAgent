import { useState } from 'react'
import type { GraphNode } from '@/types/graph'

interface Props {
  label: string
  selectedNode: GraphNode | null
  availableNodes: GraphNode[]
  allNodes: GraphNode[]
  onSelect: (nodeId: string) => void
}

export function JobPickerButton({ label, selectedNode, availableNodes, allNodes, onSelect }: Props) {
  const [open, setOpen] = useState(false)
  const unavailableNodes = allNodes.filter(n => !availableNodes.includes(n))

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-full border border-slate-300 py-3 px-4 text-left hover:border-slate-900 transition-colors cursor-pointer"
      >
        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">
          {label}
        </div>
        <div className="text-[15px] font-semibold text-slate-900 truncate">
          {selectedNode ? selectedNode.label : '选一个岗位 ↓'}
        </div>
      </button>

      {open && (
        <div className="absolute left-0 right-0 mt-1 border border-slate-200 bg-white shadow-lg z-10 max-h-[400px] overflow-y-auto">
          {availableNodes.length === 0 && unavailableNodes.length === 0 && (
            <div className="px-4 py-3 text-[13px] text-slate-400">
              暂无可对比岗位，请稍后重试
            </div>
          )}
          {availableNodes.map(n => (
            <button
              key={n.node_id}
              onClick={() => { onSelect(n.node_id); setOpen(false) }}
              className="block w-full text-left px-4 py-2.5 text-[14px] text-slate-900 hover:bg-slate-100 cursor-pointer"
            >
              {n.label}
              <span className="text-[11px] text-slate-400 ml-2">· {n.role_family}</span>
            </button>
          ))}
          {unavailableNodes.length > 0 && (
            <div className="border-t border-slate-200 pt-2 pb-1 px-4 text-[10px] uppercase tracking-widest text-slate-400">
              叙事建设中
            </div>
          )}
          {unavailableNodes.map(n => (
            <div
              key={n.node_id}
              className="block w-full text-left px-4 py-2 text-[13px] text-slate-300 cursor-not-allowed"
            >
              {n.label}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
