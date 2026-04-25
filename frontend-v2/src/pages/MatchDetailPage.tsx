import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { ChevronLeft, Check, AlertCircle, RefreshCw, Target, TrendingUp, Compass } from 'lucide-react'
import { fetchMatchDetail, type MatchDetail } from '@/api/recommendations'

const CHANNEL_LABEL: Record<string, { icon: React.ReactNode; label: string }> = {
  entry: { icon: <Target style={{ width: 12, height: 12, display: 'inline-block', marginRight: 2 }} />, label: '起步岗位' },
  growth: { icon: <TrendingUp style={{ width: 12, height: 12, display: 'inline-block', marginRight: 2 }} />, label: '成长目标' },
  explore: { icon: <Compass style={{ width: 12, height: 12, display: 'inline-block', marginRight: 2 }} />, label: '探索方向' },
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
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadData() }, [roleId]) // eslint-disable-line react-hooks/exhaustive-deps

  const roleLabel = data?.label || searchParams.get('label') || roleId || ''
  const channel = searchParams.get('channel') as string | undefined
  const zone = searchParams.get('zone') as string | undefined

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
        <div style={{ width: 32, height: 32, border: '2px solid var(--border)', borderTopColor: 'var(--dark)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <p style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>正在加载分析结果...</p>
        <style>{`
          @keyframes spin { to { transform: rotate(360deg); } }
        `}</style>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
        <AlertCircle style={{ width: 40, height: 40, color: 'var(--accent)' }} />
        <p style={{ color: 'var(--text-secondary)' }}>{error || '数据不存在'}</p>
        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={loadData} className="btn btn-primary">重试</button>
          <button onClick={() => navigate(-1)} className="btn btn-ghost">返回</button>
        </div>
      </div>
    )
  }

  if (data.failed) {
    return (
      <div className="container" style={{ paddingBottom: 48 }}>
        <div style={{ paddingTop: 32 }}>
          <button
            onClick={() => navigate(-1)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 14, color: 'var(--text-tertiary)', background: 'none', border: 'none', cursor: 'pointer', marginBottom: 24 }}
          >
            <ChevronLeft style={{ width: 16, height: 16 }} /> 返回画像
          </button>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '64px 0', gap: 16 }}>
            <AlertCircle style={{ width: 48, height: 48, color: '#d97706' }} />
            <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>「{roleLabel}」分析暂时未成功</p>
            <p style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>AI 模型响应超时，点击重新分析</p>
            <button onClick={loadData} className="btn btn-primary" style={{ marginTop: 8 }}>
              <RefreshCw style={{ width: 16, height: 16 }} /> 重新分析
            </button>
          </div>
        </div>
      </div>
    )
  }

  const highGaps = data.gaps.filter((g) => g.priority === 'high')
  const medGaps = data.gaps.filter((g) => g.priority === 'medium')
  const lowGaps = data.gaps.filter((g) => g.priority === 'low')
  const medCount = medGaps.length
  const lowCount = lowGaps.length

  const summaryReason = (data as any).reason || ''

  return (
    <div style={{ paddingBottom: 48 }}>
      <div className="container" style={{ paddingTop: 32 }}>
        {/* Back */}
        <button
          onClick={() => navigate(-1)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            fontSize: 14,
            color: 'var(--text-tertiary)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            marginBottom: 24,
            transition: 'color 0.2s',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--text-primary)' }}
          onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-tertiary)' }}
        >
          <ChevronLeft style={{ width: 16, height: 16 }} /> 返回画像
        </button>

        {/* Hero */}
        <div style={{ marginBottom: 48 }}>
          <div className="caption" style={{ marginBottom: 16, letterSpacing: '0.12em' }}>岗位匹配分析</div>

          <div style={{ display: 'flex', gap: 10, marginBottom: 28, flexWrap: 'wrap' }}>
            {channel && CHANNEL_LABEL[channel] && (
              <span className="tag">
                {CHANNEL_LABEL[channel].icon}{CHANNEL_LABEL[channel].label}
              </span>
            )}
            {zone && ZONE_LABEL[zone] && (
              <span className="tag tag-solid">{ZONE_LABEL[zone].text}</span>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 80, alignItems: 'start' }}>
            <div>
              <h1 className="display" style={{ fontWeight: 700 }}>
                与你匹配的<br />
                <span className="underline" style={{ color: 'var(--accent)', textDecorationColor: 'var(--accent)' }}>{roleLabel}</span>
              </h1>
            </div>
            <div style={{ paddingTop: 12 }}>
              <p className="body-large">
                {summaryReason || `基于你的项目经验和技术栈，这个岗位与你的匹配度处于${zone ? ZONE_LABEL[zone]?.text || zone : '中等'}。核心框架你已掌握，主要缺口在性能优化和工程化深度。`}
              </p>
            </div>
          </div>

          <div className="stat-row">
            <div>
              <div className="stat-num">{data.mastered_count}</div>
              <div className="stat-label">已掌握模块</div>
            </div>
            <div>
              <div className="stat-num">{data.gap_count}</div>
              <div className="stat-label">需补强</div>
            </div>
            <div>
              <div className="stat-num">{medCount + lowCount}</div>
              <div className="stat-label">建议关注</div>
            </div>
          </div>
        </div>

        <hr className="divider" />

        {/* Dark feature card */}
        <section className="section">
          <div className="dark-section anim">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48, alignItems: 'center' }}>
              <div>
                <div className="caption" style={{ color: 'rgba(255,255,255,0.5)', marginBottom: 12 }}>技能匹配分析</div>
                <h2 className="headline" style={{ marginBottom: 16 }}>你的核心优势</h2>
                <p className="body-large" style={{ marginBottom: 24 }}>
                  {data.mastered.length > 0
                    ? `你已掌握 ${data.mastered_count} 个核心模块，${data.mastered.slice(0, 3).map((m) => m.module).join('、')} 是你的强项。继续在这些基础上拓展，可以快速建立竞争优势。`
                    : '基础能力扎实，核心框架已有一定积累。继续深化现有技能，同时有针对性地补充缺口。'}
                </p>
                <button className="btn btn-ghost" style={{ borderColor: 'rgba(255,255,255,0.2)', color: '#fff' }}>
                  查看详细分析 →
                </button>
              </div>
              <div className="placeholder">[image: 技能雷达图或可视化]</div>
            </div>
          </div>
        </section>

        <hr className="divider" />

        {/* Two-column layout: mastered + gaps */}
        <section className="section" style={{ paddingTop: 0 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 3fr', gap: 24 }}>
            {/* Left: mastered */}
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: '#15803d' }}>已掌握</h3>
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: '#15803d',
                    background: '#dcfce7',
                    padding: '2px 10px',
                    borderRadius: 100,
                  }}
                >
                  {data.mastered_count}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {data.mastered.length > 0 ? (
                  data.mastered.map((item, i) => (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: 10,
                        padding: '10px 12px',
                        borderRadius: 10,
                        background: 'rgba(220,252,231,0.5)',
                      }}
                    >
                      <Check style={{ width: 16, height: 16, color: '#16a34a', flexShrink: 0, marginTop: 2 }} strokeWidth={2.5} />
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 500, color: '#14532d', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.module}</div>
                        <div style={{ fontSize: 11, color: 'rgba(20,83,45,0.7)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.reason}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: 13, color: 'var(--text-tertiary)', padding: '8px 0' }}>暂无已掌握模块</div>
                )}
              </div>
            </div>

            {/* Right: gaps */}
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>建议学习</h3>
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: '#b45309',
                    background: '#fef3c7',
                    padding: '2px 10px',
                    borderRadius: 100,
                  }}
                >
                  {data.gap_count}
                </span>
              </div>

              {/* High priority */}
              {highGaps.length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <div
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: '#b45309',
                      marginBottom: 10,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b' }} />
                    高优先级 · 建议优先学习
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {highGaps.map((item, i) => (
                      <div
                        key={i}
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: 10,
                          padding: '10px 12px',
                          borderRadius: 10,
                          background: 'rgba(254,243,199,0.5)',
                          border: '1px solid rgba(251,191,36,0.2)',
                        }}
                      >
                        <span
                          style={{
                            width: 20,
                            height: 20,
                            borderRadius: '50%',
                            background: '#fef3c7',
                            fontSize: 11,
                            fontWeight: 700,
                            color: '#b45309',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                            marginTop: 1,
                          }}
                        >
                          {i + 1}
                        </span>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{item.module}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.reason}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Medium priority */}
              {medGaps.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: 'var(--text-tertiary)',
                      marginBottom: 10,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#60a5fa' }} />
                    建议补充
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {medGaps.map((item, i) => (
                      <span
                        key={i}
                        style={{
                          fontSize: 11,
                          background: 'var(--bg)',
                          border: '1px solid var(--border)',
                          color: 'var(--text-secondary)',
                          padding: '4px 10px',
                          borderRadius: 8,
                        }}
                      >
                        {item.module}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Low priority */}
              {lowGaps.length > 0 && (
                <div>
                  <div
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: 'var(--text-tertiary)',
                      marginBottom: 10,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      opacity: 0.6,
                    }}
                  >
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--border)' }} />
                    锦上添花
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {lowGaps.map((item, i) => (
                      <span
                        key={i}
                        style={{
                          fontSize: 11,
                          color: 'var(--text-tertiary)',
                          padding: '4px 10px',
                          borderRadius: 8,
                          background: 'rgba(0,0,0,0.02)',
                        }}
                      >
                        {item.module}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {data.gaps.length === 0 && (
                <div style={{ fontSize: 13, color: 'var(--text-tertiary)', padding: '8px 0' }}>无建议学习模块</div>
              )}
            </div>
          </div>
        </section>

        <hr className="divider" />

        {/* CTA */}
        <section style={{ padding: '48px 0 80px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, alignItems: 'end' }}>
            <div>
              <h2 className="headline" style={{ marginBottom: 12 }}>下一步</h2>
              <p className="body-large" style={{ maxWidth: 440 }}>在技能图谱中查看完整路径，或在成长档案中追踪学习进度。</p>
            </div>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              <button onClick={() => navigate(`/graph?node=${encodeURIComponent(roleId!)}`)} className="btn btn-ghost">
                去图谱查看
              </button>
              <button onClick={() => navigate('/growth-log')} className="btn btn-primary">
                去成长档案追踪
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
