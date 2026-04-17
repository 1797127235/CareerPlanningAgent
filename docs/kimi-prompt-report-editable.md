# Kimi 执行：报告全章可编辑 + 智能润色 + 完整性检查

## 背景

报告页当前 Chapter I/II/III 已支持编辑（有 `onSave` + 编辑按钮），但 Chapter IV（行动计划）不可编辑。
另外缺少"智能润色"按钮和"完整性检查"功能。需要补齐这三个能力。

---

## 任务 1：Chapter IV 支持编辑

**文件**: `frontend/src/components/report/ChapterIV.tsx`

### 当前状态
- Chapter IV 只展示行动计划（阶段 + 行动项），没有 `onSave` 回调
- 行动计划的数据结构是 `data.action_plan.stages[]`，每个 stage 有 `items[]`

### 需要做的

Chapter IV 的行动计划是结构化数据（不是纯文本），所以编辑方式和前三章不同。
采用"整体叙事编辑"模式：用户可以编辑 chapter-4 的叙事概述文本。

（a）给 ChapterIV 加 `onSave` 和 `saving` props（和 ChapterI 一样的模式）：

```typescript
interface ChapterIVProps {
  data: ReportV2Data
  onSave?: (text: string) => Promise<void>
  saving?: boolean
}
```

（b）在 Chapter IV 的标题区域加一个"编辑"按钮。点击后显示 textarea，
用户可以编辑行动计划的补充说明文本。

参考 `ChapterI.tsx` 的编辑模式实现（lines 44-119）——完全相同的模式：
- `useState` 管理 `editing` 和 `draft`
- `enterEdit()` 进入编辑，`cancel()` 退出，`save()` 保存
- 编辑态显示 textarea + 保存/取消按钮
- 非编辑态显示编辑铅笔按钮

编辑的内容来源：`data.chapter_narratives?.['chapter-4'] || ''`
如果用户从未编辑过，textarea 默认空，placeholder 写"为行动计划添加补充说明或调整建议"。

（c）编辑内容显示在行动计划列表上方，作为一段概述文字。

### ReportPage.tsx 的改动

找到 `<ChapterIV data={data} />`（约第 486 行），改为：

```tsx
<ChapterIV
  data={data}
  onSave={(t) => saveChapter('chapter-4', t)}
  saving={saving}
/>
```

---

## 任务 2：智能润色按钮

**文件**: `frontend/src/pages/ReportPage.tsx`

### 当前状态
- 后端已有 `POST /report/{id}/polish` 端点（润色 narrative 文本）
- 前端已有 `polishReport(id)` API 函数
- Epilogue 组件底部可能已有润色入口，但不明显

### 需要做的

在报告页的 Epilogue 区域（报告底部），增加一个明显的"智能润色"按钮。

找到 `<Epilogue` 组件的使用位置（约第 487 行），确认 Epilogue 是否已有 `onPolish` prop。

如果没有，在 `ReportPage.tsx` 中给 Epilogue 传 `onPolish`：

```tsx
<Epilogue
  generatedAt={data.generated_at}
  onRegenerate={generate}
  onPolish={async () => {
    if (currentId == null) return
    setSaving(true)
    try {
      const result = await polishReport(currentId)
      setData((prev) => prev ? { ...prev, narrative: result.narrative || prev.narrative } : prev)
      setToast({ message: '润色完成', type: 'success', durationMs: 2000 })
    } catch (e) {
      setToast({ message: '润色失败', type: 'error', durationMs: 3000 })
    } finally {
      setSaving(false)
    }
  }}
  polishing={saving}
/>
```

然后在 `Epilogue.tsx` 组件内，加一个"智能润色"按钮：

```tsx
{onPolish && (
  <button
    onClick={onPolish}
    disabled={polishing}
    className="inline-flex items-center gap-2 text-[13px] font-semibold text-slate-600 hover:text-blue-700 transition-colors cursor-pointer disabled:opacity-50"
  >
    <Sparkles className="w-3.5 h-3.5" />
    {polishing ? '润色中…' : '智能润色'}
  </button>
)}
```

需要在 Epilogue 的 props 里加 `onPolish?: () => void` 和 `polishing?: boolean`。
从 lucide-react 导入 `Sparkles` 图标。

**注意**：先检查 `polishReport` 的返回值格式。阅读 `frontend/src/api/report.ts` 里的 `polishReport` 函数，确认返回类型。

---

## 任务 3：完整性检查

**文件**: `frontend/src/pages/ReportPage.tsx`

### 需要做的

在报告 Prologue（报告顶部，生成时间/导出按钮区域），加一个完整性检查提示。

检查逻辑（纯前端，不需要后端）：

```typescript
function getCompletenessIssues(data: ReportV2Data): string[] {
  const issues: string[] = []
  if (!data.narrative?.trim()) issues.push('第一章"你是谁"缺少叙事')
  if (!data.career_alignment?.observations?.length) issues.push('第二章"你能去哪"缺少分析')
  if (!data.differentiation_advice?.trim()) issues.push('第三章"差距"缺少差异化建议')
  if (!data.action_plan?.stages?.length) issues.push('第四章"下一步"缺少行动计划')
  if (!data.market?.salary_p50) issues.push('缺少市场数据')
  return issues
}
```

在 Prologue 区域（导出按钮旁边），如果有 issues，显示一个小提示：

```tsx
{issues.length > 0 && (
  <div className="mt-3 px-4 py-2.5 rounded-lg bg-amber-50 border border-amber-100 text-[12px] text-amber-700">
    <span className="font-semibold">完整性提示：</span>
    {issues.join('；')}
  </div>
)}
```

如果所有检查通过，显示一个绿色的"报告完整"标记：

```tsx
{issues.length === 0 && (
  <span className="inline-flex items-center gap-1 text-[12px] text-emerald-600 font-medium">
    <CheckCircle className="w-3.5 h-3.5" /> 报告完整
  </span>
)}
```

---

## 文件改动清单

| 文件 | 改动 |
|------|------|
| `frontend/src/components/report/ChapterIV.tsx` | 加 onSave/saving props + 编辑 UI |
| `frontend/src/pages/ReportPage.tsx` | ChapterIV 传 onSave + 润色逻辑 + 完整性检查 |
| `frontend/src/components/report/Epilogue.tsx` | 加润色按钮 |

---

## 关键参考文件

| 文件 | 看什么 |
|------|--------|
| `frontend/src/components/report/ChapterI.tsx` | **核心参考**——编辑模式的完整实现模式 |
| `frontend/src/pages/ReportPage.tsx` L248-274 | saveChapter() 函数 |
| `frontend/src/api/report.ts` | polishReport() 返回值格式 |
| `backend/routers/report.py` L214-244 | PATCH 端点如何处理 chapter_narratives |

---

## 验收标准

1. Chapter IV 右上角有"编辑"铅笔按钮 → 点击出现 textarea → 保存后内容持久化
2. 报告底部有"智能润色"按钮 → 点击后 loading 态 → 完成后第一章文本更新
3. 报告顶部显示完整性检查结果：缺章节时显示黄色提示，全部完整时显示绿色"报告完整"
4. 已有的 Chapter I/II/III 编辑功能不受影响
5. TypeScript 编译无错误

## 不要做

- 不改后端（PATCH 端点已支持 `chapter_narratives` 任意 key）
- 不改数据库
- 不改报告生成逻辑
- 不加新 npm 依赖
