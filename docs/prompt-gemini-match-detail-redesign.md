# Gemini 前端任务：MatchDetailPage 重写（方案B — 双栏对比）

## 目标

重写 `frontend/src/pages/MatchDetailPage.tsx`，采用双栏对比布局 + 横向进度条。

## 设计参考

打开 `demos/match-detail-B.html` 查看完整静态 demo。核心布局：

### Header 区域
- 左侧：角色中文名（大字）、channel 标签（起步岗位/成长目标/探索方向）、zone 标签（安全区/杠杆区等）
- 右侧：匹配度大字数字（如 22%），下方小字"掌握 5 / 23 模块"
- 底部：横向进度条（蓝色渐变，宽度 = coverage_pct%）
- 进度条下方：一句话总结（来自 LLM reason）

### 双栏主体（grid grid-cols-5）
**左栏 col-span-2：已掌握**
- 白底圆角卡片，标题"已掌握"+ 数量 badge
- 每个模块：绿色勾 + 模块名 + 短理由，紧凑排列（bg-emerald-50/50 圆角行）

**右栏 col-span-3：建议学习**
- 白底圆角卡片，标题"建议学习"+ 数量 badge
- 按优先级分3层：
  - **高优先级**：编号列表（1、2、3...），每项有模块名 + 短理由，amber 背景
  - **建议补充**：紧凑 tag/chip 展示（text-[11px]，bg-slate-50 border），不展开理由
  - **锦上添花**：更淡的 tag（text-slate-400），一行展示

### 底部 CTA
- 两个按钮并排：去图谱查看该岗位 / 查看学习资源

## API

```typescript
// 已有，无需修改
import { fetchMatchDetail, type MatchDetail, type MatchAnalysisResult } from '@/api/recommendations'

// GET /api/recommendations/match-analysis/{roleId}
// 返回：
interface MatchDetail {
  role_id: string
  label?: string        // 中文名，如 "Rust 工程师"
  mastered: Array<{ module: string; reason: string }>
  gaps: Array<{ module: string; reason: string; priority: 'high' | 'medium' | 'low' }>
  mastered_count: number
  gap_count: number
  coverage_pct: number
  failed?: boolean      // LLM 分析失败标记
}
```

## 补充信息来源

channel 和 zone 信息不在 detail API 返回中，从 sessionStorage 获取：

```typescript
const summaryCard = useMemo<MatchAnalysisResult | undefined>(() => {
  try {
    const cached = sessionStorage.getItem('match_analysis_results')
    if (!cached) return undefined
    const results: MatchAnalysisResult[] = JSON.parse(cached)
    return results.find(r => r.role_id === roleId)
  } catch { return undefined }
}, [roleId])

const channel = summaryCard?.channel   // 'entry' | 'growth' | 'explore'
const zone = summaryCard?.zone         // 'safe' | 'leverage' | 'transition' | 'danger'
```

Channel 标签映射：
```
entry → 起步岗位, growth → 成长目标, explore → 探索方向
```

Zone 标签映射：
```
safe → 安全区(green), leverage → 杠杆区(blue), transition → 过渡区(amber), danger → 危险区(red)
```

## 状态处理

必须处理 4 个状态：

1. **loading**：居中 spinner + "正在加载分析结果..."
2. **error**：错误信息 + 重试按钮 + 返回按钮
3. **failed**（`data.failed === true`）：显示角色名 + "分析暂时未成功" + 重新分析按钮（点击调 loadData 重新请求）
4. **success**：正常双栏布局

重试逻辑：
```typescript
const loadData = () => {
  if (!roleId) return
  setLoading(true)
  setError(null)
  setData(null)  // 必须清空，否则 failed 状态不会消失
  fetchMatchDetail(roleId)
    .then(setData)
    .catch(e => setError(e instanceof Error ? e.message : '加载失败'))
    .finally(() => setLoading(false))
}
```

## 路由

已注册，无需修改：`/profile/match/:roleId`

## 样式规范

- 全站蓝色主题：`var(--blue)` 或 `blue-600`
- 圆角卡片用 `bg-white rounded-2xl border border-slate-100 shadow-sm`（不用 glass）
- 页面背景 `bg-slate-50`
- 最大宽度 `max-w-[900px]`
- 紧凑间距，不要大卡片大留白
- 不用 emoji 做图标，用 lucide-react

## 不要做的事

- 不要修改 API 层代码
- 不要修改路由注册
- 不要自动加载，只在 useEffect 中根据 roleId 加载一次
- 不要用 emoji 图标
