# 报告页 Hero 区 & 市场竞争力模块重构方案

> **目标**：用 `graph.json` 中 curated 的 `project_recommendations` / `differentiation_advice` / `ai_impact_narrative` 替代当前空洞的「匹配分 + 四维卡片 + 技能条形图」陈列，让报告页形成以**“具体项目推荐”为核心叙事**的体验。
> 
> **作者**：Kimi（供 Claude 审核）
> 
> **影响文件**：`backend/services/report_service.py` + `frontend/src/pages/ReportPage.tsx`

---

## 一、当前问题诊断（已确认）

### 1. Hero 区信息断层
- 只有一个 `ScoreRing` 匹配分 + 三个市场指标小卡片（需求变化/薪资增长/中位月薪）。
- 市场指标和学生的**个人情况无关**，占据首屏黄金位置却无行动价值。
- `skill_gap.core` 覆盖率只显示一行小字，没有和“下一步该做什么”建立关联。

### 2. 市场竞争力分析模块空洞
- `SkillGapSection` 下半部的“优先补强技能”用条形图展示 JD 出现频率（如“高并发 40%”）。
- 这对用户的唯一价值是：**知道招聘方爱写什么词**；但它不回答**“我做什么项目能补上这个词”**。
- 条形图本质上是数据展示，不是行动指导。

### 3. 高质量 curated 数据被埋没
- `graph.json` 每个节点都有 `project_recommendations`（带 `name` + `why`）、`differentiation_advice`、`ai_impact_narrative`。
- 这些数据是**中文、具体、由脚本/团队校准过的**，但目前在报告页**完全未被消费**。

---

## 二、重构后的信息架构

报告页首屏及向下滚动的新叙事顺序：

```
1. AI 综合评价（保留，已有）
2. 目标岗位诊断台（Hero 区，重构）      ← 核心改动
   ├── 岗位名称 + 核心技能覆盖
   ├── 2-3 个具体项目推荐卡片（来自 graph.json）
   └── 锚点：查看岗位详情 / 生成完整计划
3. 方向对齐分析（CareerAlignmentSection，已有）
4. 市场竞争力分析（SkillGapSection，重构）  ← 核心改动
   ├── 技能覆盖 tier bars（保留但去侵略色）
   ├── 已掌握技能标签矩阵（简化 badge）
   └── 项目驱动的缺口清单（新增，替代条形图）
5. AI 影响与护城河（新增独立卡片）        ← 新增
6. 档案体检（diagnosis，已有）
7. 个性化成长计划（action_plan，已有）
```

---

## 三、后端改动：`backend/services/report_service.py`

### 3.1 在 `generate_report()` 的 `report_data` 中新增字段

当前 `report_data` 缺少 graph 节点的 curated 叙事数据。在现有 `report_data` 里追加：

```python
report_data = {
    # ... 已有字段保持不变 ...
    "career_alignment": career_alignment,
    # 新增：
    "differentiation_advice": node.get("differentiation_advice", ""),
    "ai_impact_narrative": node.get("ai_impact_narrative", ""),
    "project_recommendations": node.get("project_recommendations", [])[:3],
    # generated_at ...
}
```

**类型说明**：
- `differentiation_advice: str` — 差异化建议文本，如"选一个垂直方向深入：实现一个简化版秒杀系统..."
- `ai_impact_narrative: str` — AI 影响分析，如"AI 对前端影响最直接：Cursor/Copilot 已经能生成 80% 的页面代码..."
- `project_recommendations: list[dict]` — 最多 3 个，每项结构 `{"name": str, "why": str}`

### 3.2 不删除的字段
- `skill_gap`、`action_plan`、`career_alignment`、`market`、`delta` 全部保留，供现有模块使用。
- `soft_skills` 保留。
- 不涉及数据库迁移。

---

## 四、前端改动：`frontend/src/pages/ReportPage.tsx`

### 4.1 `ReportData` interface 扩展

```typescript
interface ReportData {
  // ... 已有字段
  differentiation_advice?: string
  ai_impact_narrative?: string
  project_recommendations?: { name: string; why: string }[]
}
```

### 4.2 Hero 区重构（原 796-869 行区域）

**删掉的内容**：
- 市场三指标卡片（市场需求变化 / 薪资年增长率 / 市场中位月薪）**从 Hero 区移除**。
- `ScoreRing` 的尺寸从 136 降级为 80-100，或移到左侧小角落，不再占首屏 C 位。

**Hero 区新结构**：

```tsx
<motion.div variants={fadeUp} className="glass p-6">
  <div className="g-inner flex flex-col gap-5">
    
    {/* 顶部：岗位名 + 匹配分小字 + 核心覆盖 */}
    <div className="flex items-start justify-between">
      <div>
        <p className="text-[11px] text-slate-400 mb-1">目标岗位</p>
        <h2 className="text-xl font-bold text-slate-800">{data.target?.label}</h2>
        {data.skill_gap?.core && (
          <p className="text-[13px] text-slate-500 mt-1">
            核心技能 {data.skill_gap.core.matched}/{data.skill_gap.core.total} 覆盖
            {data.skill_gap.has_project_data && ` · ${data.skill_gap.core.practiced_count} 个有项目证据`}
          </p>
        )}
      </div>
      <ScoreRing score={data.match_score ?? 0} size={80} />
    </div>

    {/* 中轴：项目推荐卡片（核心） */}
    {data.project_recommendations && data.project_recommendations.length > 0 && (
      <div className="space-y-3">
        <p className="text-[12px] font-semibold text-slate-700">建议优先建立的实战经验</p>
        {data.project_recommendations.map((proj, idx) => (
          <div key={idx} className="rounded-xl p-3.5 border border-indigo-100/60 bg-indigo-50/30">
            <p className="text-[13px] font-semibold text-indigo-900">{proj.name}</p>
            <p className="text-[11.5px] text-slate-600 leading-relaxed mt-1">{proj.why}</p>
            {/* 关联的缺口技能（轻量规则匹配，见 4.5） */}
            <ProjectGapTags projectName={proj.name} topMissing={data.skill_gap?.top_missing || []} />
          </div>
        ))}
      </div>
    )}

    {/* 底部：差异化建议一句话摘要 */}
    {data.differentiation_advice && (
      <div className="text-[12px] text-slate-600 leading-relaxed px-3 py-2 bg-slate-50/60 rounded-lg border border-slate-100">
        <span className="font-medium text-slate-700">差异化方向：</span>
        {data.differentiation_advice.slice(0, 80)}
        {data.differentiation_advice.length > 80 && '…'}
      </div>
    )}

    {/* 市场 timing badge 保留但缩小 */}
    {data.market && (
      <div className="flex items-center gap-2">
        <TimingBadge timing={data.market.timing} label={data.market.timing_label} />
        <button onClick={() => navigate(`/roles/${data.target?.node_id}`)} className="text-[11px] text-blue-600 hover:underline">
          查看岗位详情 →
        </button>
      </div>
    )}

  </div>
</motion.div>
```

### 4.3 市场竞争力分析（`SkillGapSection`）重构

#### A. Tier bars 颜色修正
- 核心技能：红 `#dc2626` → **靛蓝 `#4f46e5`**
- 重要技能：保持琥珀 `#d97706`（或微调为 `#f59e0b`）
- 加分技能：保持蓝 `#2563eb`

#### B. 已掌握技能标签墙简化
当前标签内嵌 badge 导致长短不一。改为：
- 标签本身只用 subtle 背景色
- 状态用标签**左侧 3px 竖条**或**底部 2px 细线**表示
- `实战验证` / `简历声称` 的图例统一放在标签墙下方一行

```tsx
<div className="flex flex-wrap gap-2">
  {gap.matched_skills.map(skill => (
    <span key={skill.name} className="relative px-2.5 py-1 rounded-md bg-white/60 text-[12px] text-slate-700 border border-slate-100">
      <span className="absolute left-0 top-1.5 bottom-1.5 w-[2.5px] rounded-r-full" style={{ background: statusColor[skill.status] }} />
      <span className="pl-1.5">{skill.name}</span>
    </span>
  ))}
</div>
```

#### C. 用「项目驱动的缺口清单」替代「优先补强技能条形图」

**删除**：原有 `gap.top_missing` 条形图（橙/蓝横条 + 百分比）。

**新增**：

```tsx
{data.project_recommendations && data.project_recommendations.length > 0 && (
  <div className="mt-5 pt-5 border-t border-slate-100">
    <p className="text-[12px] font-semibold text-slate-700 mb-3">按项目补齐缺口</p>
    <div className="space-y-3">
      {data.project_recommendations.map((proj, idx) => {
        const covered = inferCoveredSkills(proj.name, data.skill_gap?.top_missing || [])
        return (
          <div key={idx} className="flex items-start gap-3">
            <div className="mt-0.5 w-5 h-5 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-[10px] font-bold">{idx + 1}</div>
            <div className="flex-1">
              <p className="text-[12.5px] font-medium text-slate-800">{proj.name}</p>
              {covered.length > 0 && (
                <p className="text-[11px] text-slate-500 mt-0.5">
                  可覆盖缺口：{covered.map(s => s.name).join(' · ')}
                </p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  </div>
)}
```

### 4.4 新增「AI 影响与护城河」卡片

渲染位置：在 `SkillGapSection` 之后、`ActionPlan` 之前。

```tsx
{data.ai_impact_narrative && data.differentiation_advice && (
  <motion.div variants={fadeUp} className="glass p-5">
    <div className="g-inner space-y-4">
      <div className="flex items-center gap-2 mb-1">
        <Cpu size={15} className="text-violet-500" />
        <p className="text-[13px] font-semibold text-slate-700">AI 影响与护城河</p>
      </div>
      
      <div className="text-[12.5px] text-slate-700 leading-relaxed px-3 py-2.5 bg-violet-50/40 rounded-lg border border-violet-100/60">
        {data.ai_impact_narrative}
      </div>
      
      <div>
        <p className="text-[11px] font-medium text-slate-500 mb-1">差异化方向</p>
        <p className="text-[12px] text-slate-700 leading-relaxed">{data.differentiation_advice}</p>
      </div>
    </div>
  </motion.div>
)}
```

### 4.5 辅助逻辑：项目与缺口的轻量匹配

不需要 LLM，用简单规则即可：

```typescript
function inferCoveredSkills(projectName: string, topMissing: MissingSkill[]) {
  // 建立项目名 -> 可能关联的技能关键词映射（可扩展）
  const keywordMap: Record<string, string[]> = {
    '秒杀': ['高并发', 'Redis', '消息队列', '性能优化', '分布式锁'],
    '存储引擎': ['内存管理', '性能优化', '数据结构', '数据库'],
    'RPC': ['分布式系统', '网络编程', 'gRPC'],
    'CRDT': ['数据结构', '网络编程', 'JavaScript'],
    'APM': ['性能优化', '内存管理', 'Android'],
    'RAG': ['AI', 'Python', '向量数据库', 'NLP'],
  }
  
  const hits = new Set<string>()
  for (const [kw, skills] of Object.entries(keywordMap)) {
    if (projectName.includes(kw)) {
      skills.forEach(s => hits.add(s))
    }
  }
  
  // 在 topMissing 中找到被命中的
  return topMissing.filter(m => {
    const name = m.name
    return Array.from(hits).some(h => name.includes(h) || h.includes(name))
  }).slice(0, 3)
}
```

---

## 五、用户验证标准（DoD）

生成报告后，用户应该看到：

1. **Hero 区不再有三个市场小卡片**，而是直接显示 2-3 个具体项目推荐。
2. **每个项目卡片有名称、why 描述、可覆盖的缺口技能**。
3. **市场竞争力分析里不再有条形图显示"高并发 40%"**，而是显示"按项目补齐缺口"的清单。
4. **已掌握技能的标签不再有内部 badge 挤压**，而是统一的圆角标签 + 左侧竖线。
5. **新增独立的「AI 影响与护城河」卡片**，引用 `ai_impact_narrative` + `differentiation_advice`。
6. **核心技能 tier bar 颜色不再是正红色**。

---

## 六、风险与回滚

| 风险 | 规避方式 |
|------|---------|
| `project_recommendations` 对某些管理岗偏难 | 后端保留全部数据，前端仅在 `career_level <= 3` 或 `project_recommendations` 非空时渲染该区块；否则回退到只展示 `differentiation_advice` 摘要 |
| `inferCoveredSkills` 规则漏匹配 | 这不是阻塞性问题，漏匹配时前端只显示项目名和 why，不显示"可覆盖缺口"小字即可 |
| 用户习惯了旧的市场三指标 | 市场指标可降级移到「岗位详情页」或报告页底部，不在首屏 |

---

## 七、Claude 的审核要点

请 Claude 重点审以下 4 点：

1. **"用项目推荐替代市场指标放在首屏"** 这个信息架构决策是否对用户有商业价值，还是只是设计师自嗨？
2. **`inferCoveredSkills` 这种简单关键字匹配是否够用**，还是应该在后端生成报告时就预计算好"项目 -> 缺口技能"的关联？
3. **AI 影响卡片放在 `SkillGapSection` 和 `ActionPlan` 之间**这个位置是否合理？会不会打断用户的行动流？
4. **是否有遗漏的 edge case**（比如 `project_recommendations` 为空、`differentiation_advice` 过长、`ai_impact_narrative` 为空等）？
