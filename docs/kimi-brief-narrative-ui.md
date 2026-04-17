# Kimi 执行提示词：岗位图谱展示叙事卡片 + 探索页解除灰显

## 背景

我们给 45 个岗位节点都写好了 `contextual_narrative` 六字段数据（之前只有 15 个，现在全覆盖）。需要做两件事：

1. **RoleDetailPage** 展示叙事数据——目前只有一个"对比相似方向"链接，没有展示实际内容
2. **ExplorePage 的 JobPickerButton** 解除灰显——之前 30 个没数据的节点是灰色不可选，现在全部可选

---

## 改动清单（共 3 个文件）

### 改动 1：`frontend/src/pages/RoleDetailPage.tsx`

#### 1a. 在 RoleDetail 接口中添加 contextual_narrative 类型

找到 `interface RoleDetail` 定义（大约第 118-171 行），在 `market_signal?` 字段之前或之后添加：

```typescript
  contextual_narrative?: {
    what_you_actually_do: string
    what_drains_you: string
    three_year_outlook: string
    who_fits: string
    ai_impact_today: string
    common_entry_path: string
  }
```

注意：这个接口可能已经有 `contextual_narrative` 的引用（第 658 行用了 `data.contextual_narrative`），但接口定义里可能没有类型声明。加上确保 TypeScript 不报错。

#### 1b. 在 "市场洞察" 区块之后、"对比相似方向"链接之前，插入叙事卡片

找到第 658 行附近的代码：

```tsx
          {data.contextual_narrative && (
            <>
              <div className="border-t border-slate-100" />
              <div className="text-center py-2">
                <Link
                  to={`/explore?left=${data.node_id}`}
                  className="text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 transition-colors"
                >
                  对比相似方向 →
                </Link>
              </div>
            </>
          )}
```

**替换为**：

```tsx
          {data.contextual_narrative && (
            <>
              <div className="border-t border-slate-100" />
              <div className="px-5 py-4">
                <h3 className="text-[13px] font-bold text-slate-900 mb-4">这个方向真实的样子</h3>
                <div className="space-y-3">
                  {([
                    { key: 'what_you_actually_do', label: '你每天真正在做的事', color: 'blue' },
                    { key: 'what_drains_you',      label: '什么会耗尽你',       color: 'amber' },
                    { key: 'three_year_outlook',    label: '三年后的你',         color: 'emerald' },
                    { key: 'who_fits',              label: '适合什么样的人',     color: 'violet' },
                    { key: 'ai_impact_today',       label: 'AI 对这个方向的影响', color: 'rose' },
                    { key: 'common_entry_path',     label: '常见入行路径',       color: 'slate' },
                  ] as const).map(({ key, label, color }) => {
                    const text = (data.contextual_narrative as Record<string, string>)?.[key]
                    if (!text) return null
                    return (
                      <div key={key} className={`rounded-xl bg-${color}-50/50 border border-${color}-100 px-4 py-3`}>
                        <p className={`text-[10px] text-${color}-500 font-bold uppercase tracking-wider mb-1.5`}>{label}</p>
                        <p className="text-[12px] text-slate-600 leading-[1.7]">{text}</p>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="border-t border-slate-100" />
              <div className="text-center py-2">
                <Link
                  to={`/explore?left=${data.node_id}`}
                  className="text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 transition-colors"
                >
                  对比相似方向 →
                </Link>
              </div>
            </>
          )}
```

**⚠ Tailwind 动态类名问题**：Tailwind 不能识别模板字符串拼接的类名（如 `` bg-${color}-50/50 ``）。有两种解决方案：

**方案 A（推荐）**：用完整的静态类名映射，替代动态拼接：

```tsx
const NARRATIVE_FIELDS = [
  { key: 'what_you_actually_do', label: '你每天真正在做的事', bg: 'bg-blue-50/50', border: 'border-blue-100', text: 'text-blue-500' },
  { key: 'what_drains_you',      label: '什么会耗尽你',       bg: 'bg-amber-50/50', border: 'border-amber-100', text: 'text-amber-500' },
  { key: 'three_year_outlook',    label: '三年后的你',         bg: 'bg-emerald-50/50', border: 'border-emerald-100', text: 'text-emerald-500' },
  { key: 'who_fits',              label: '适合什么样的人',     bg: 'bg-violet-50/50', border: 'border-violet-100', text: 'text-violet-500' },
  { key: 'ai_impact_today',       label: 'AI 对这个方向的影响', bg: 'bg-rose-50/50', border: 'border-rose-100', text: 'text-rose-500' },
  { key: 'common_entry_path',     label: '常见入行路径',       bg: 'bg-slate-50/50', border: 'border-slate-100', text: 'text-slate-500' },
] as const

// 然后在 JSX 中：
{NARRATIVE_FIELDS.map(({ key, label, bg, border, text }) => {
  const content = (data.contextual_narrative as Record<string, string>)?.[key]
  if (!content) return null
  return (
    <div key={key} className={`rounded-xl ${bg} border ${border} px-4 py-3`}>
      <p className={`text-[10px] ${text} font-bold uppercase tracking-wider mb-1.5`}>{label}</p>
      <p className="text-[12px] text-slate-600 leading-[1.7]">{content}</p>
    </div>
  )
})}
```

把 `NARRATIVE_FIELDS` 放在组件外面作为常量。

**方案 B**：如果项目用了 Tailwind 的 `safelist`，可以用动态拼接，但需要在 `tailwind.config` 里加 safelist。不推荐。

### 改动 2：`frontend/src/components/explore/JobPickerButton.tsx`

**目的**：移除灰显逻辑——现在所有节点都有叙事数据，不需要区分 available/unavailable。

但实际上 `JobPickerButton` 本身不需要改——它只是接收 `availableNodes` 和 `allNodes` 两个 prop。灰显逻辑在 **ExplorePage.tsx** 里。

### 改动 3：`frontend/src/pages/ExplorePage.tsx`

找到第 36-38 行：

```tsx
  const availableNodes = useMemo(
    () => (graphData?.nodes ?? []).filter(n => n.contextual_narrative),
    [graphData?.nodes],
  )
```

**改成**（所有节点都 available）：

```tsx
  const availableNodes = useMemo(
    () => graphData?.nodes ?? [],
    [graphData?.nodes],
  )
```

这样 `JobPickerButton` 的 `unavailableNodes`（allNodes - availableNodes）就自动变成空数组，灰显区域自然消失。

---

## 不需要改的文件

- ❌ `frontend/src/components/explore/JobPickerButton.tsx` — 逻辑自动适配
- ❌ `frontend/src/components/explore/ComparisonRow.tsx` — 不变
- ❌ 后端任何文件 — `contextual_narrative` 已经在 API 返回里
- ❌ `frontend/src/types/graph.ts` — `ContextualNarrative` 接口已定义

---

## 验证

1. **岗位图谱详情页**：打开任意岗位（如 `/roles/golang`），应该看到 6 张叙事卡片（每天做什么、消耗因素、三年展望、适合谁、AI 影响、入行路径），颜色各异
2. **探索对比页**：打开 `/explore`，下拉选岗位时应该看到全部 45 个节点都可选（没有灰显的"叙事建设中"分组）
3. **样式**：叙事卡片的视觉风格应该和现有的"市场洞察"区域的卡片（如 `ai_impact_narrative`、`career_ceiling`）保持一致——圆角、浅色背景、小号标题 + 正文

---

## 总结

| # | 文件 | 改动 |
|---|------|------|
| 1 | `frontend/src/pages/RoleDetailPage.tsx` | 接口加 `contextual_narrative` 类型 + 插入 6 字段叙事卡片 |
| 2 | `frontend/src/pages/ExplorePage.tsx` | `availableNodes` 过滤条件去掉 `contextual_narrative` 检查 |

无新增文件。无后端改动。
