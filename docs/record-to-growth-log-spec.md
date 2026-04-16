# 报告 IV · 下一步 "记到成长档案 →" 按钮直接落库 spec（交给 Kimi 执行）

## 问题

`frontend/src/components/report/ChapterIV.tsx` 里每条行动的"记到成长档案 →"按钮，当前实现是：

```tsx
onClick={() => navigate('/growth-log', { state: { prefill: prefillText } })}
```

**跳到 `/growth-log` 页面，在 QuickInput 的 textarea 里预填 `item.action || item.text`。**

用户还得手动：
1. 在 QuickInput 里选一个标签（#项目 / #面试 / #学习 或自定义）——否则 `handleSend` 直接 `setErrorMsg('请至少选一个标签…')` 拒绝
2. 点"发送"

如果用户以为按钮文案 "记到成长档案" 就是真在记录，回头发现档案里什么都没有。断层。

## 修复方向

按钮点击后**直接调用 API 落库**，不再跳转。成功后按钮变成"已记入 ✓"禁用状态。失败显示内联错误 + 重试。

### 记录内容规则

每条行动记一条 `GrowthEntry`，字段映射：

| 字段 | 值 |
|---|---|
| `content` | `item.action \|\| item.text`（同原 prefill 逻辑） |
| `category` | `'learning'`（所有类型统一走 learning 通道，和 QuickInput 的快速发送一致） |
| `tags` | 按 `item.type` 映射：`skill` → `['学习', '来自报告']`；`project` → `['项目', '来自报告']`；`job_prep` → `['求职', '来自报告']` |
| `structured_data` | `null` |
| `is_plan` | `true` |
| `status` | `'pending'` |
| `due_type` | `'daily'` |
| `due_at` | 今天 23:59:59 的 ISO 字符串（参见 `QuickInput.tsx` 里 `dueType === 'daily'` 分支的实现） |
| `completed_at` | `null` |
| `ai_suggestions` | `null` |

"来自报告" 这个标签用来后续区分记录来源，方便以后筛选。

## 需要改的文件

**只改一个文件：`frontend/src/components/report/ChapterIV.tsx`**

其它文件不要动。后端 API（`POST /growth-log/entries`）已支持；前端有 `createEntry` 函数（在 `frontend/src/api/growthEntries.ts`）和 `useGrowthEntries` hook（在 `frontend/src/components/growth-log-v2/useEntries.ts`），复用即可。

**重要：不要在 `ChapterIV` 里调 `useGrowthEntries()`**——那个 hook 内部有 `useQuery(listEntries)`，会让每次打开报告都请求一遍成长档案列表，而报告页压根用不到列表数据。只用 `useMutation` 直接包 `createEntry` 即可。

## 具体改动

### 改动 1：`ActionArticle` 组件加一个 mutation + 本地状态

在 `ActionArticle` 组件内部（或抽到 `ChapterIV` 顶层也行，但每个 item 独立 mutation 状态更直观，放进 `ActionArticle` 最干净）：

1. 引入 React Query 的 `useMutation` + `useQueryClient`，以及 API 函数 `createEntry`：
   ```ts
   import { useMutation, useQueryClient } from '@tanstack/react-query'
   import { createEntry } from '@/api/growthEntries'
   import type { GrowthEntry } from '@/components/growth-log-v2/mockData'
   ```
2. 在 `ActionArticle` 内部建立 mutation（每个 article 独立一份 state，天然互相隔离）：
   ```ts
   const qc = useQueryClient()
   const mutation = useMutation({
     mutationFn: (data: Partial<GrowthEntry>) => createEntry(data),
     onSuccess: () => {
       qc.invalidateQueries({ queryKey: ['growth-entries'] })
     },
   })
   const saving = mutation.isPending
   const saved = mutation.isSuccess
   const errorMsg = mutation.isError
     ? (mutation.error instanceof Error ? mutation.error.message : String(mutation.error))
     : null
   ```
   `invalidateQueries(['growth-entries'])` **必须加**——这样用户切到 `/growth-log` 时 `GrowthLogV2Page` 里的 `useGrowthEntries()` 会自动重新拉列表，看到刚记的条目。
3. 点击按钮时的处理函数 `handleRecord`：
   - 如果 `saving || saved` 直接 return（防抖 + 防重复）
   - 根据 `item.type` 选 tag：
     ```ts
     const tagByType: Record<string, string[]> = {
       skill: ['学习', '来自报告'],
       project: ['项目', '来自报告'],
       job_prep: ['求职', '来自报告'],
     }
     const tags = tagByType[item.type] || ['学习', '来自报告']
     ```
   - 构造今天末尾 ISO：
     ```ts
     const d = new Date()
     d.setHours(23, 59, 59, 999)
     const due_at = d.toISOString()
     ```
   - 调 `mutation.mutate({ content: item.action || item.text, category: 'learning', tags, structured_data: null, is_plan: true, status: 'pending', due_type: 'daily', due_at, completed_at: null, ai_suggestions: null })`
   - mutation 本身自带 `isPending / isSuccess / isError`，不需要额外写 try/catch 和 console.error（失败信息通过 `mutation.error` 拿）

### 改动 2：按钮 UI 三态

按钮替换原来的单一 `navigate` 逻辑，根据状态渲染：

```tsx
{saved ? (
  <span className="mt-2 inline-flex items-center gap-1 text-[13px] font-semibold text-emerald-700 border-b-2 border-emerald-700 pb-0.5">
    已记入成长档案 ✓
  </span>
) : (
  <button
    onClick={handleRecord}
    disabled={saving}
    className="mt-2 inline-flex items-center gap-1 text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors cursor-pointer"
  >
    {saving ? '记录中…' : '记到成长档案 →'}
  </button>
)}
{errorMsg && (
  <p className="mt-1 text-[12px] text-red-700">
    记录失败：{errorMsg}，
    <button
      onClick={handleRecord}
      className="underline hover:text-red-900 cursor-pointer"
    >
      点这里重试
    </button>
  </p>
)}
```

### 改动 3：移除 `navigate` 相关代码

`ActionArticle` 里原来的：
```tsx
const navigate = useNavigate()
const prefillText = item.action || item.text
```
删掉。`useNavigate` 的 import（在文件顶部 `import { useNavigate } from 'react-router-dom'`）如果文件里没别的地方用了，整行删掉。如果别处还用，则只删 `ActionArticle` 里那一行调用。

**核对 import 顶部**：改完后 `ChapterIV.tsx` 的 imports 大致应该是：
```ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createEntry } from '@/api/growthEntries'
import type { GrowthEntry } from '@/components/growth-log-v2/mockData'
import type { ReportV2Data, PlanActionItem, PlanStage } from '@/api/report'
import { ChapterOpener, Chapter } from './index'
```
（`useNavigate` 移除）

## 验收标准

1. 在报告 IV · 下一步章节，点击任意一条行动的"记到成长档案 →"按钮：
   - 按钮立即变"记录中…"禁用
   - 1-2 秒后变成绿色"已记入成长档案 ✓"（不可再点）
   - 不跳转页面，用户停留在报告
2. 跳转到 `/growth-log`，新记录出现在时间线上，带 `#学习` / `#项目` / `#求职` + `#来自报告` 标签，status=pending，due=今日
3. 断网时点击 → 下方红字错误 + "点这里重试"链接
4. 同一条记录按钮重复快速点击 → 只产生一条记录（防抖有效）
5. 不同行动的按钮状态互相独立（点击 A 不影响 B 的按钮）
6. 手动去 `/growth-log` 用 QuickInput 输入 + 选标签 + 发送的流程**完全不受影响**
7. 报告其它部分（I/II/III 章节）不受影响

## 不要做

- 不要改后端（`backend/routers/growth_log.py` / `backend/services/growth_log_service.py`）
- 不要改 `useGrowthEntries` hook（位于 `frontend/src/components/growth-log-v2/useEntries.ts`）
- 不要改 `GrowthLogV2Page.tsx` 和 `QuickInput.tsx`
- 不要动 `navigate('/growth-log', { state: { prefill } })` 的其它调用点（如果别处还有）
- 不要加 toast / 通知组件——成功状态靠按钮自身变绿 + 打勾，失败靠下方红字，不引入新的 UI 概念
- 不要在 `App.tsx` 或路由配置里做任何变更
- 不要在 `ActionArticle` 里调 `useGrowthEntries()`（会触发不必要的 listEntries 请求）——按改动 1 用 `useMutation + createEntry` 的组合

---

改完跑前端 `npm run dev`，打开报告，点任意一条"记到成长档案 →"，按钮要变绿打勾，然后去 `/growth-log` 看到新记录。
