import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { ChevronLeft, Check, AlertCircle, RefreshCw, Target, TrendingUp, Compass } from 'lucide-react'
import { fetchMatchDetail, type MatchDetail } from '@/api/recommendations'

const CHANNEL_LABEL: Record<string, { icon: React.ReactNode; label: string }> = {
  entry: { icon: <Target className="w-3 h-3 inline-block mr-0.5" />, label: '起步岗位' },
  growth: { icon: <TrendingUp className="w-3 h-3 inline-block mr-0.5" />, label: '成长目标' },
  explore: { icon: <Compass className="w-3 h-3 inline-block mr-0.5" />, label: '探索方向' },
}

const ZONE_LABEL: Record<string, { text: string; cls: string }> = {
  safe: { text: '安全区', cls: 'bg-green-100 text-green-700' },
  leverage: { text: '杠杆区', cls: 'bg-blue-100 text-blue-700' },
  transition: { text: '过渡区', cls: 'bg-amber-100 text-amber-700' },
  danger: { text: '危险区', cls: 'bg-red-100 text-red-700' },
}

export default function MatchDetailPage() {
  const { roleId } = useParams<{ roleId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [data, setData] = useState<MatchDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = () => {
    if (!roleId) return
    setLoading(true)
    setError(null)
    setData(null)
    fetchMatchDetail(roleId)
      .then(setData)
      .catch(e => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadData() }, [roleId]) // eslint-disable-line react-hooks/exhaustive-deps

  const roleLabel = data?.label || searchParams.get('label') || roleId || ''
  const channel = searchParams.get('channel') as string | undefined
  const zone = searchParams.get('zone') as string | undefined

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 border-2 border-[var(--blue)] border-t-transparent rounded-full animate-spin" />
        <p className="text-[13px] text-slate-500">正在加载分析结果...</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-10 h-10 text-red-400" />
        <p className="text-slate-600">{error || '数据不存在'}</p>
        <div className="flex gap-3">
          <button onClick={loadData} className="bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700 cursor-pointer">重试</button>
          <button onClick={() => navigate(-1)} className="text-slate-500 text-sm hover:underline cursor-pointer">返回</button>
        </div>
      </div>
    )
  }

  if (data.failed) {
    return (
      <div className="pb-12">
        <div className="max-w-[900px] mx-auto pt-8 px-4 sm:px-6">
          <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-slate-500 hover:text-slate-800 transition-colors mb-6 text-sm font-medium cursor-pointer">
            <ChevronLeft className="w-4 h-4" /> 返回画像
          </button>
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            <AlertCircle className="w-12 h-12 text-amber-400" />
            <p className="text-[15px] font-medium text-slate-700">「{roleLabel}」分析暂时未成功</p>
            <p className="text-[13px] text-slate-400">AI 模型响应超时，点击重新分析</p>
            <button onClick={loadData} className="mt-2 bg-blue-600 text-white text-[14px] font-semibold px-6 py-2.5 rounded-xl hover:bg-blue-700 cursor-pointer flex items-center gap-2">
              <RefreshCw className="w-4 h-4" /> 重新分析
            </button>
          </div>
        </div>
      </div>
    )
  }

  const highGaps = data.gaps.filter(g => g.priority === 'high')
  const medGaps = data.gaps.filter(g => g.priority === 'medium')
  const lowGaps = data.gaps.filter(g => g.priority === 'low')
  const totalModules = data.mastered_count + data.gap_count

  const summaryReason = (data as any).reason || ''

  return (
    <div className="pb-12">
      <div className="max-w-[900px] mx-auto pt-8 px-4 pb-12">
        <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-800 text-sm font-medium mb-6 cursor-pointer transition-colors">
          <ChevronLeft className="w-4 h-4" /> 返回画像
        </button>

        {/* Header */}
        <div className="glass p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{roleLabel}</h1>
              <div className="flex items-center gap-2 mt-1">
                {channel && CHANNEL_LABEL[channel] && (
                  <span className="text-[11px] font-semibold bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full flex items-center">
                    {CHANNEL_LABEL[channel].icon}{CHANNEL_LABEL[channel].label}
                  </span>
                )}
                {zone && ZONE_LABEL[zone] && (
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${ZONE_LABEL[zone].cls}`}>
                    {ZONE_LABEL[zone].text}
                  </span>
                )}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[40px] font-black text-blue-600 leading-none">
                {data.coverage_pct}<span className="text-[20px]">%</span>
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                掌握 {data.mastered_count} / {totalModules} 模块
              </div>
            </div>
          </div>
          {/* Progress bar */}
          <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-500 ease-out" 
              style={{ width: `${data.coverage_pct}%` }} 
            />
          </div>
          {summaryReason && (
            <p className="text-[13px] text-slate-500 mt-3">{summaryReason}</p>
          )}
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          
          {/* Left: mastered (2 cols) */}
          <div className="md:col-span-2">
            <div className="glass p-5 h-full">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-[14px] font-bold text-emerald-700">已掌握</h2>
                <span className="text-[12px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                  {data.mastered_count}
                </span>
              </div>
              
              <div className="space-y-2.5">
                {data.mastered.length > 0 ? (
                  data.mastered.map((item, i) => (
                    <div key={i} className="flex items-center gap-2.5 bg-emerald-50/50 rounded-lg px-3 py-2.5">
                      <Check className="w-4 h-4 text-emerald-500 shrink-0" strokeWidth={2.5} />
                      <div className="min-w-0">
                        <div className="text-[13px] font-medium text-emerald-800 truncate">{item.module}</div>
                        <div className="text-[11px] text-emerald-600/70 truncate">{item.reason}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-[13px] text-slate-400 py-2">暂无已掌握模块</div>
                )}
              </div>
            </div>
          </div>

          {/* Right: gaps (3 cols) */}
          <div className="md:col-span-3">
            <div className="glass p-5 h-full">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-[14px] font-bold text-slate-800">建议学习</h2>
                <span className="text-[12px] font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">
                  {data.gap_count}
                </span>
              </div>

              {/* Priority: High */}
              {highGaps.length > 0 && (
                <div className="mb-4">
                  <div className="text-[11px] font-bold text-amber-600 mb-2 flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-amber-500"></div> 高优先级 · 建议优先学习
                  </div>
                  <div className="space-y-1.5">
                    {highGaps.map((item, i) => (
                      <div key={i} className="flex items-start gap-2.5 px-3 py-2 rounded-lg bg-amber-50/50 border border-amber-100/50">
                        <span className="text-[11px] font-bold text-amber-600 bg-amber-100 w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5">
                          {i + 1}
                        </span>
                        <div className="min-w-0">
                          <div className="text-[13px] font-semibold text-slate-800">{item.module}</div>
                          <div className="text-[11px] text-slate-500 truncate">{item.reason}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Priority: Medium - compact */}
              {medGaps.length > 0 && (
                <div className="mb-3">
                  <div className="text-[11px] font-bold text-slate-400 mb-2 flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-blue-400"></div> 建议补充
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {medGaps.map((item, i) => (
                      <span key={i} className="text-[11px] bg-slate-50 border border-slate-200 text-slate-600 px-2.5 py-1 rounded-lg">
                        {item.module}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Priority: Low - just tags */}
              {lowGaps.length > 0 && (
                <div>
                  <div className="text-[11px] font-bold text-slate-300 mb-2 flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-slate-200"></div> 锦上添花
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {lowGaps.map((item, i) => (
                      <span key={i} className="text-[11px] text-slate-400 px-2.5 py-1 rounded-lg bg-slate-50/50">
                        {item.module}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {data.gaps.length === 0 && (
                <div className="text-[13px] text-slate-400 py-2">无建议学习模块</div>
              )}
            </div>
          </div>

        </div>

        {/* CTA */}
        <div className="flex flex-col sm:flex-row gap-3 mt-6 pt-6 border-t border-slate-200">
          <button
            onClick={() => navigate(`/graph?node=${encodeURIComponent(roleId!)}`)}
            className="flex-1 bg-white border border-slate-300 text-slate-700 text-[14px] font-semibold py-3 rounded-xl flex items-center justify-center gap-2 hover:bg-slate-50 transition-colors cursor-pointer"
          >
            去图谱查看该岗位
          </button>
          <button
            onClick={() => navigate('/growth-log')}
            className="flex-1 bg-blue-600 text-white text-[14px] font-semibold py-3 rounded-xl flex items-center justify-center gap-2 hover:bg-blue-700 transition-colors cursor-pointer"
          >
            去成长档案追踪
          </button>
        </div>

      </div>
    </div>
  )
}
