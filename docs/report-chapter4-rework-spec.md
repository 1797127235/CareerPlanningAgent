# 发展报告 第四章（下一步）改造 spec

> **问题**：当前第四章只展示 3 条行动项，丢失 skill 产出的 3 阶段结构（0-2 周/2-6 周/6-12 周），而且每条是观察句不是行动项，"记到成长档案"按钮粘过去没法执行。
> **目标**：三阶段时间线 + 每条 item 拆成「观察 + 行动」两个字段
> **范围**：1 个 skill 改 prompt，1 个前端组件重写，1 个类型定义扩展，1 个 pipeline 字段兼容

---

## §1 Skill 改造：`action-plan/SKILL.md`

### 1.1 输出格式改动

**当前**每条 item：
```json
{ "id": "item-1-1", "type": "skill", "text": "观察句 60-150字", "tag": "短标签",
  "priority": "high", "phase": 1, "evidence_ref": "M-003" }
```

**新**每条 item（新增 `action` 字段）：
```json
{
  "id": "item-1-1",
  "type": "skill",
  "observation": "你在字节二面被问到 Redis 持久化时卡在 RDB/AOF 差异上，说明这块知识只停留在名词层。",
  "action": "3 天内画出 RDB vs AOF 触发机制的对比图，并做 2 道相关面试题。",
  "tag": "Redis 持久化",
  "priority": "high",
  "phase": 1,
  "evidence_ref": "pain:0"
}
```

**字段说明：**
- `observation`：观察句，60-150 字，承袭原 `text` 字段的约束（禁止祈使句，必须挂钩证据）
- `action`：祈使句行动项，30-80 字，**必须具体**（有时间/动作/产出），不能抽象
- `tag`：短标签，5-12 字，用作卡片 headline
- 保留 `text` 为**兼容字段**，值 = `observation`（向后兼容旧前端代码）

### 1.2 Prompt 修改

**SKILL.md 的 System 段硬约束改动：**

原第 3 条：
```
3. **观察句**，禁止祈使句。禁止以"完成/搭建/..."开头。
```

改为：
```
3. **每条 item 必须同时包含 observation 和 action 两段**：
   - observation：观察句，60-150 字，陈述"你做了 X / 遇到 Y / 还缺 Z"，禁止祈使句
   - action：行动项，30-80 字，祈使句，必须有动作动词 + 具体范围 + 时间或产出
     正例："3 天内整理 RDB vs AOF 对比图，做 2 道相关面试题"
     反例："加强 Redis 学习"（没有具体动作）/ "掌握 Redis 持久化"（没有时间/产出）
```

原第 6 条：
```
6. 每条 text 60-150 字，要有"为什么"和"会怎样"。
```

改为：
```
6. observation 60-150 字，描述"为什么要做这件事"（基于具体行为信号）；
   action 30-80 字，描述"具体怎么做"（可立即执行的动作）。
   observation 不是 action 的重复，两者互补。
```

### 1.3 输出 schema 部分

把 SKILL.md 里的输出示例改为：
```json
{
  "stages": [
    {
      "stage": 1,
      "label": "立即整理",
      "duration": "0-2周",
      "milestone": "一句话里程碑：这两周做完了应该能达到什么状态",
      "items": [
        {
          "id": "item-1-1",
          "type": "skill|project|job_prep",
          "observation": "观察句，60-150 字",
          "action": "祈使行动句，30-80 字",
          "tag": "短标签 5-12 字",
          "priority": "high|medium|low",
          "phase": 1,
          "evidence_ref": "M-003"
        }
      ]
    },
    { "stage": 2, ... },
    { "stage": 3, ... }
  ]
}
```

---

## §2 后端兼容：`pipeline.py._coerce_action_plan`

### 2.1 新增字段填充

现有代码只处理了 `text` / `evidence_ref`。新增 `observation` / `action` 的兜底：

```python
def _coerce_action_plan(raw: dict) -> dict:
    stages = raw.get("stages", [])
    while len(stages) < 3:
        stages.append({
            "stage": len(stages) + 1,
            "label": ["立即整理", "技能补强", "项目冲刺与求职"][len(stages)],
            "duration": ["0-2周", "2-6周", "6-12周"][len(stages)],
            "milestone": "",
            "items": [],
        })
    for stg in stages[:3]:
        for it in stg.get("items", []):
            # 新字段兜底：老模型可能只给 text，没给 observation/action
            obs = it.get("observation") or it.get("text", "")
            act = it.get("action") or ""
            it["observation"] = _sanitize_action_text(obs)
            it["action"] = (act or "").strip()
            # 兼容字段：保留 text = observation
            it["text"] = it["observation"]
            if "evidence_ref" not in it:
                it["evidence_ref"] = ""
    return {
        "stages": stages[:3],
        "skills": [it for s in stages for it in s.get("items", []) if it.get("type") == "skill"],
        "project": [it for s in stages for it in s.get("items", []) if it.get("type") == "project"],
        "job_prep": [it for s in stages for it in s.get("items", []) if it.get("type") == "job_prep"],
    }
```

### 2.2 fallback 也要填

`pipeline.py` action-plan skill 调用失败时走的 `action_plan._build_action_plan()`，那个函数也要确保 items 有 `observation` 和 `action` 字段。如果 fallback 生成的只有 `text`：
- `observation` = `text`
- `action` = `text`（规则式兜底没办法拆分，至少让字段存在不让前端崩）

---

## §3 前端类型扩展：`frontend/src/api/report.ts`

找到 `PlanActionItem` 类型（应该在 report.ts 里），新增字段：

```typescript
export interface PlanActionItem {
  id: string
  type: 'skill' | 'project' | 'job_prep'
  text: string              // 兼容保留 = observation
  observation: string       // 新增：观察句
  action: string            // 新增：行动项
  tag?: string
  priority?: 'high' | 'medium' | 'low'
  phase?: number
  evidence_ref?: string
  done?: boolean
}

export interface PlanStage {
  stage: number             // 1 | 2 | 3
  label: string             // "立即整理"
  duration: string          // "0-2周"
  milestone: string         // 一句话里程碑
  items: PlanActionItem[]
}
```

确保 `ReportV2Data.action_plan.stages: PlanStage[]` 类型正确。

---

## §4 前端渲染重写：`frontend/src/components/report/ChapterIV.tsx`

### 4.1 整页结构

替换当前的「扁平 3 条」渲染为「三阶段时间线」：

```
┌──────────────────────────────────────────┐
│ IV · 下一步                                │
│ 先从这一件开始。                             │
├──────────────────────────────────────────┤
│                                          │
│ ─────── 阶段一 · 0-2 周 ─────────          │
│ 立即整理                                   │
│ 里程碑: 简历能投了，基础面题能答了         │
│                                          │
│ ┌─ [技能] Redis 持久化 · 优先             │
│ │ 观察：你在字节二面被问到 Redis...        │
│ │ 行动：3 天内画出 RDB vs AOF 对比图...    │
│ │                  [记到成长档案 →]        │
│ └─                                       │
│                                          │
│ ┌─ [求职] 简历 bullet 优化 · 优先          │
│ │ 观察：你做了两个项目但简历里...          │
│ │ 行动：给每个项目补一段 STAR 结构...      │
│ │                  [记到成长档案 →]        │
│ └─                                       │
│                                          │
│ ─────── 阶段二 · 2-6 周 ─────────          │
│ 技能补强                                   │
│ 里程碑: ...                                │
│                                          │
│ (stage 2 items...)                       │
│                                          │
│ ─────── 阶段三 · 6-12 周 ────────          │
│ 项目冲刺与求职                              │
│                                          │
│ (stage 3 items...)                       │
└──────────────────────────────────────────┘
```

### 4.2 组件实现

```tsx
import { useNavigate } from 'react-router-dom'
import type { ReportV2Data, PlanActionItem, PlanStage } from '@/api/report'
import { ChapterOpener, Chapter } from './index'

const TYPE_LABEL: Record<string, string> = {
  skill: '技能',
  project: '项目',
  job_prep: '求职',
}

function StageHeader({ stage }: { stage: PlanStage }) {
  return (
    <div className="mt-12 first:mt-0">
      <div className="flex items-baseline gap-3 mb-2">
        <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-blue-600">
          阶段{['一', '二', '三'][stage.stage - 1] || stage.stage}
        </span>
        <span className="text-[11px] font-medium text-slate-400 tabular-nums">
          {stage.duration}
        </span>
      </div>
      <h2 className="text-[28px] font-bold text-slate-900 tracking-tight leading-[1.2]">
        {stage.label}
      </h2>
      {stage.milestone && (
        <p className="mt-2 text-[14px] text-slate-500 italic leading-relaxed">
          里程碑：{stage.milestone}
        </p>
      )}
    </div>
  )
}

function ActionArticle({ item }: { item: PlanActionItem }) {
  const navigate = useNavigate()

  // prefill 成长档案用 action 而不是 observation
  const prefillText = item.action || item.text

  return (
    <article className="mt-6 pt-5 border-t border-slate-200">
      <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 mb-2">
        [{TYPE_LABEL[item.type] ?? '行动'}]
        {item.priority === 'high' && (
          <span className="ml-2 text-blue-600">· 优先</span>
        )}
      </p>
      {item.tag && (
        <h3 className="text-[18px] font-bold text-slate-900 tracking-tight mb-3">
          {item.tag}
        </h3>
      )}
      {item.observation && (
        <div className="mb-3">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">观察</span>
          <p className="mt-1 text-[14px] text-slate-700 leading-relaxed max-w-[60ch]">
            {item.observation}
          </p>
        </div>
      )}
      {item.action && (
        <div className="mb-3">
          <span className="text-[11px] font-bold text-blue-600 uppercase tracking-wider">行动</span>
          <p className="mt-1 text-[14px] text-slate-900 leading-relaxed max-w-[60ch] font-medium">
            {item.action}
          </p>
        </div>
      )}
      <button
        onClick={() => navigate('/growth-log', { state: { prefill: prefillText } })}
        className="mt-2 inline-flex items-center gap-1 text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700 transition-colors cursor-pointer"
      >
        记到成长档案 →
      </button>
    </article>
  )
}

export function ChapterIV({ data }: { data: ReportV2Data }) {
  const stages: PlanStage[] = data.action_plan?.stages ?? []

  const hasAny = stages.some(s => (s.items || []).length > 0)

  return (
    <div id="chapter-4">
      <ChapterOpener numeral="IV" label="下一步" headline="从阶段一开始，一步步往下走。" />
      <Chapter>
        {!hasAny ? (
          <p className="text-[15px] text-slate-500">
            行动方案正在生成中。你可以先回到岗位图谱，了解目标方向需要哪些核心技能。
          </p>
        ) : (
          <div className="space-y-4">
            {stages.map((stage, i) => (
              <section key={i}>
                <StageHeader stage={stage} />
                <div className="mt-4">
                  {(stage.items || []).map((item, j) => (
                    <ActionArticle key={item.id || `${i}-${j}`} item={item} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </Chapter>
    </div>
  )
}
```

### 4.3 兼容性保底

如果 `item.observation` 和 `item.action` 都不存在（老数据），至少要展示 `item.text`：

```tsx
// 在 ActionArticle 里
const hasStructured = item.observation || item.action
return (
  <article ...>
    {/* ... header ... */}
    {hasStructured ? (
      <>
        {item.observation && <ObservationBlock text={item.observation} />}
        {item.action && <ActionBlock text={item.action} />}
      </>
    ) : (
      // fallback: 老数据只有 text
      <p className="text-[14px] text-slate-700 leading-relaxed max-w-[60ch]">
        {item.text}
      </p>
    )}
    {/* ... button ... */}
  </article>
)
```

---

## §5 成长档案 prefill 接入

ChapterIV 的"记到成长档案"按钮传 `state: { prefill }`。确认 `GrowthLogV2Page` 读到后把 prefill 文本填进 `QuickInput` 的 textarea：

```tsx
// GrowthLogV2Page.tsx 顶部
import { useLocation } from 'react-router-dom'

const location = useLocation()
const prefillText = (location.state as { prefill?: string } | null)?.prefill || ''

// 传给 QuickInput
<QuickInput initialText={prefillText} />
```

`QuickInput` 组件如果还没支持 `initialText` prop，要加上：

```tsx
export function QuickInput({ initialText = '' }: { initialText?: string }) {
  const [content, setContent] = useState(initialText)
  useEffect(() => {
    if (initialText) setContent(initialText)
  }, [initialText])
  // ...
}
```

---

## §6 验收清单

### Skill

1. ☐ 手动调 `invoke_skill("action-plan", ...)`，返回的每条 item 有 `observation` + `action` 两个字段
2. ☐ `action` 是祈使句且 30-80 字，包含具体动作 + 时间/产出
3. ☐ `observation` 60-150 字，非祈使句
4. ☐ stages 保持 3 个，每个有 `duration` 和 `milestone`

### Pipeline

1. ☐ `_coerce_action_plan` 处理 LLM 返回的 JSON，为缺失 `observation`/`action` 的 item 兜底填充
2. ☐ fallback（LLM 失败时）生成的 items 也有 `observation` 和 `action` 字段（哪怕等于 text）

### 前端

1. ☐ `/report?id=xxx` 看到第四章三阶段时间线结构
2. ☐ 每个 stage 显示 `阶段X · 0-2周` + label + milestone
3. ☐ 每条 item 显示 tag 标题 + 观察段 + 行动段
4. ☐ "记到成长档案 →" 按钮跳转到 `/growth-log`，输入框里已填入 action 文本
5. ☐ 老报告（没有 observation/action 字段）仍能渲染（fallback 到 text）
6. ☐ `npm run build` 零 TS 错误

---

## §7 执行边界

1. **不改** `action_plan.py`（规则式 fallback 模块）的核心逻辑，只在 `_coerce_action_plan` 末尾统一兜底字段
2. **不删** `action_plan.skills` / `action_plan.project` / `action_plan.job_prep` 这三个扁平字段（其他组件可能在用）
3. **不改** ChapterOpener / Chapter 等基础组件
4. **保留** 老报告的兼容性（用 text 字段兜底）

---

## §8 开工前先回一句

看完 spec 回："文档读完，准备开工"。

如果有不确定，先问：
- `action_plan.py` 规则式 fallback 里加 `observation`/`action` 字段时遇到阻碍？先停下沟通
- 老报告 data_json 里的 item 结构和你实际看到的不一致？先贴一条真实数据看看
