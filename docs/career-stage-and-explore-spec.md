# Spec：职业阶段感知 + 岗位对比探索

## 背景

当前系统让学生在**还不懂岗位的情况下**就被要求选目标岗位和上传画像，中间有个巨大的鸿沟。岗位图谱提供了 45 张参数卡片（薪资、技能、zone），但这是**决策后的确认信息**，不是**决策前的建构信息**。学生打开系统 10 分钟得不到任何"这个岗位究竟意味着什么"的理解，就关掉浏览器去小红书读帖子了。

本 spec 解决两件事：
1. **系统自动感知学生所处的职业阶段**（探索 / 聚焦 / 求职 / 冲刺），不让学生自己贴标签
2. **新增"对比探索"路径**：针对"探索"阶段学生，用叙事型的两两岗位对比替代参数表卡片，帮他们真正理解 2026 年的岗位实际形态

## MVP 范围（第一版做什么）

### Must
1. 后端 `career_stage` 自动判定 + `/me/stage` 端点
2. `graph.json` 每个 node 增加 `contextual_narrative` 字段（6 子字段）
3. **5 个核心岗位**的 `contextual_narrative` 内容落地（内容工程）
4. 前端 `/explore` 对比探索页 + 岗位两两对比组件
5. 首页根据 `career_stage` 切第一屏主 CTA
6. `/graph` 和 `/role/:id` 增加 "跟别的方向对比" 跳转入口

### Won't（这一版明确不做）
- ❌ 个性化叙事（每个学生看到的是同一份内容；Phase 2 再考虑）
- ❌ 剩余 40 个非核心岗位的 `contextual_narrative`（等 MVP 数据验证后再补）
- ❌ 任何量化分数、进度条、雷达图、对比打分（liu 反对 gamification）
- ❌ 阶段切换时的弹窗/通知（Sally 原则：阶段变化应该静默发生）
- ❌ 对比前的"引导问题"漏斗（John 原则：先验证对比本身有用）
- ❌ 改造现有 `/graph` / `/profile` / `/report` 的主体流程（只加入口，不改结构）

### 成本估算
- 代码：3-4 人日（后端 1 日 + 前端 1.5-2 日 + 集成测试 0.5 日）
- 内容：5 岗位 × 6 字段 × ~100 字 ≈ 3000 字，LLM 草稿 + 人工审 **~13 小时**

---

## Part A：数据层改造

### A.1 `graph.json` 新增字段

在每个 node 对象里增加：

```jsonc
{
  "node_id": "ai-engineer",
  "label": "AI 工程师",
  // ... 所有原有字段保留 ...
  "contextual_narrative": {
    "what_you_actually_do": "...",        // 你每天真正在做的事
    "what_drains_you": "...",             // 什么会耗尽你
    "three_year_outlook": "...",          // 3 年后这个岗位的样子
    "who_fits": "...",                    // 什么样的人适合/不适合
    "ai_impact_today": "...",             // AI 在岗位里今天扮演什么角色
    "common_entry_path": "..."            // 大学生通常怎么切进这个岗位
  }
}
```

**MVP 范围**：只给 5 个核心岗位填入真实内容，其它 40 个节点 `contextual_narrative` 字段**缺省（不写这个 key 即可）**。

### A.2 5 个核心岗位（MVP）

选这 5 个覆盖 80% 学生首次对比需求：

| node_id | 中文标签 | 方向 |
|---|---|---|
| `java` | Java 工程师 | 后端 |
| `frontend` | 前端工程师 | 前端 |
| `ai-engineer` | AI 工程师 | AI 应用 |
| `algorithm-engineer` | 算法工程师 | 算法/研究 |
| `data-analyst` | 数据分析师 | 数据 |

后续扩到 15 个时候再补：`python`、`machine-learning`、`full-stack`、`devops`、`cyber-security`、`product-manager`、`data-engineer`、`mlops`、`ios`、`android`。

### A.3 字段写作规范（内容工程必读）

每个字段的**要回答的问题、写作陷阱、字数、样本**见下。**样本以 AI 工程师为准，其它 4 个岗位照这个风格写**。

#### 1. `what_you_actually_do` — 你每天真正在做的事

- **回答**：如果我真的坐到这个位置，8 小时在干什么？
- **写法**：**动词开头的第一人称**，具体到"读哪种 paper、跟谁吵、解决什么 bug"，不是 JD 抄写
- **陷阱**：❌ 职责清单 ❌ 美化（"用 AI 改变世界"）❌ 泛化（"做 AI 相关工作"）
- **字数**：80-120 字
- **样本**：
  > 今天你在一个 notebook 里反复调参，想把验证集 AUC 再往上推 0.3 个点。你会读两篇 arXiv 上三天前的 paper，评估值不值得复现。下午跟数据同学扯皮说你要的样本他没打标。晚上上线一个新模型，盯着监控看了 20 分钟没出事才敢睡。

#### 2. `what_drains_you` — 什么会耗尽你

- **回答**：这个岗位的隐藏成本是什么？劝退点在哪？
- **写法**：坦诚、具体、**不回避**。这是整个对比卡最有价值的一栏——学生能读到自嗨感以外的真相
- **陷阱**：❌ 通用缺点（"加班多"）❌ 所有岗位都有的（"沟通成本高"）要写这个岗位**独有**的消耗
- **字数**：60-100 字
- **样本**：
  > 最耗你的是"我这半年在调参，结果业务指标没动"的空洞感。你能跑出漂亮的离线指标，但线上转化就是涨不动，没人说你不努力，但你也拿不出贡献证据。再熬就是别人都在用 GPT 四两拨千斤，你还在手搓特征工程。

#### 3. `three_year_outlook` — 3 年后这个岗位的样子

- **回答**：我现在跳进去，到 2029 年这岗位还在吗？变成什么样？
- **写法**：**现在时 + 趋势指向**。不要写"截至 XXXX 年"这种免责条款——liu 反感这个
- **陷阱**：❌ 空洞乐观（"前景广阔"）❌ 空洞悲观（"会被 AI 取代"）要有具体分化判断
- **字数**：80-120 字
- **样本**：
  > 这个岗位正在分层。调包侠那一层在蒸发——GPT-4 就能干。活下来的是两头：一头是能从 paper 读到能跑通代码的研究型，一头是能把模型塞进业务流程解决真问题的工程型。中间那群只会调参不懂业务的，3 年后大概率在转岗或找不到工作。

#### 4. `who_fits` — 什么样的人适合 / 不适合

- **回答**：我是这类人吗？
- **写法**：**两句话格式**——"适合 X 的人 / 不适合 Y 的人"。描写**性格和偏好**，不写技能
- **陷阱**：❌ "适合热爱学习的人"（废话）❌ 写技能门槛（那是 must_skills）
- **字数**：60-100 字
- **样本**：
  > 适合**能坐住**的人——能一整天和一个 bug 死磕不烦躁。适合对"为什么"比"怎么做"更好奇的人。不适合需要即时反馈的人——模型训练一次 3 小时，你得习惯慢节奏。不适合想通过写代码改变世界的人，你 80% 时间在处理数据不是写模型。

#### 5. `ai_impact_today` — AI 在岗位里今天扮演什么角色

- **回答**：Copilot / ChatGPT 已经把这个岗位搞成什么样？
- **写法**：**三段式**——"今天 AI 在做什么 / 今天 AI 做不了什么 / 因此岗位的分工在变"。**必须现在时**，不能写"未来 AI 会……"
- **陷阱**：❌ 笼统（"AI 提高效率"）❌ 唱衰（"会被取代"）要任务级别的观察
- **字数**：80-120 字
- **样本**：
  > 今天 AI 已经能替你写 80% 的样板代码——PyTorch 训练循环、数据清洗 pipeline、评估脚本你 Copilot 两行就出。但它不能替你选问题——"该训哪个模型""这个 feature 该不该加"这种判断没法外包。所以岗位重心从"会不会写代码"在迅速往"会不会选问题"移。

#### 6. `common_entry_path` — 大学生通常怎么切进这个岗位

- **回答**：如果我选了这个方向，现实的上车路径是什么？
- **写法**：**具体、有参照**。要包含标准路径 + 至少一条**非典型路径**（非计算机专业怎么转、外行怎么进）
- **陷阱**：❌ 只说大厂（大部分人进不了）❌ "努力学习"这种废话
- **字数**：100-140 字
- **样本**：
  > 最标准路径：大三暑期进大厂算法实习（Kaggle 金牌 / 顶会一作论文是硬通货）→ 校招大厂算法岗。非典型路径：数学/物理/统计专业本科 → 读个 AI 方向研究生 → 有学历加成后进场。**最难走但可行的一条**：本科做一个有实际用户的 AI 小项目（比如上万用户的 Chrome 插件），用项目证明你能把模型变成产品——这条路不需要学历但极少人做成。

### A.4 写作流程

1. **LLM 草稿**：写脚本 `scripts/gen_contextual_narrative.py`，为每个 node 喂入 `label / role_family / career_level / must_skills` 让 qwen-plus 按上述 6 字段规范产出草稿，输出到 `data/contextual_narrative_draft.json`
2. **人工审改**：**这一步不能省**。每个岗位 6 字段全读一遍，改 LLM 的空话和套话，保留具体细节。**LLM 最容易出错的是第 2 和第 4 字段**——它默认写温和正面，审稿时要把"耗尽感"和"不适合的人"写硬一点
3. **合并回 `data/graph.json`**：写合并脚本或手动把 draft 里 5 个 node 的 `contextual_narrative` merge 进原节点
4. **同步 DB**：`python -m scripts.sync_graph_to_db`——`JobNode` 表里不需要新建列，因为 `graph.json` 是前端直接读的，后端 API 也从 `GraphService._nodes` 直接返回

---

## Part B：后端改造

### B.1 新增 `backend/services/career_stage.py`

```python
"""Determine the user's current career-planning stage from persisted signals.

Signals used (all from existing tables, no new schema):
  - Profile exists and has `target_node_id` in profile_json
  - Report count for this user
  - Interview entries in growth_log (kind='interview' or tagged '面试')
  - Offer signals in growth_log (kind='offer' or tagged 'offer')
"""
from __future__ import annotations
import json
from typing import Literal
from sqlalchemy.orm import Session
from backend.db_models import Profile, Report
# TODO: adjust import to real growth_log entry model name (likely GrowthEntry or similar)

Stage = Literal['exploring', 'focusing', 'job_hunting', 'sprinting']


def determine_stage(user_id: int, db: Session) -> Stage:
    # 1. Profile + target 是最基础的入场券
    profile = db.query(Profile).filter_by(user_id=user_id).first()
    has_profile = profile is not None and bool(profile.profile_json)
    target_node_id = None
    if has_profile:
        try:
            target_node_id = json.loads(profile.profile_json).get('target_node_id')
        except Exception:
            target_node_id = None

    if not has_profile or not target_node_id:
        return 'exploring'

    # 2. 报告 → 聚焦
    report_count = db.query(Report).filter_by(user_id=user_id).count()

    # 3. 成长档案里的面试/offer 信号
    # NOTE: GrowthEntry 的实际模型名/字段需对着现有代码校准
    from backend.db_models import GrowthEntry  # 调整为真实名
    interview_count = (
        db.query(GrowthEntry)
        .filter_by(user_id=user_id)
        .filter(GrowthEntry.kind == 'interview')
        .count()
    )
    offer_count = (
        db.query(GrowthEntry)
        .filter_by(user_id=user_id)
        .filter(GrowthEntry.kind == 'offer')
        .count()
    )

    # 4. 分档
    if offer_count > 0 or interview_count >= 3:
        return 'sprinting'
    if interview_count >= 1:
        return 'job_hunting'
    if report_count >= 1:
        return 'focusing'
    return 'focusing'
```

⚠️ **实现注意**：
- `GrowthEntry` 的**模型名和字段**要看现有 `backend/db_models.py` 实际是什么（成长档案 v2 的 entry 表）。spec 里写的是假名，动手前先对齐。
- 如果没有明确的 `kind='interview'` 字段，退而用 `tags` 包含 `面试` / `offer` 也可以

### B.2 新增端点 `/me/stage`

在 `backend/routers/user.py`（或 `profiles.py`，看现有路由结构）加：

```python
from backend.services.career_stage import determine_stage

@router.get("/me/stage")
def get_career_stage(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the user's current career-planning stage.

    Client uses this to conditionally render the homepage first-screen CTA
    and gate access to the /explore flow.
    """
    return {"stage": determine_stage(user.id, db)}
```

不缓存。每次调用重新判定——计算开销很小（3 次 count 查询）。

### B.3 `backend/routers/graph.py` 透出 `contextual_narrative`

当前 graph.py 第 109 行附近的 node 序列化 dict，加一行：

```python
"contextual_narrative": node.get("contextual_narrative"),
```

缺省时返回 `None`，前端判断是否渲染叙事内容。

### B.4 不需要改

- `db_models.py` 不动（`JobNode` 表不加列，叙事数据只存 graph.json）
- `sync_graph_to_db.py` 不动（`JobScore` / `JobNode` 不存叙事内容）
- `career-alignment` / `action-plan` / `skill-inference` 等 skill 不动

---

## Part C：前端改造

### C.1 新增 `useCareerStage()` hook

`frontend/src/hooks/useCareerStage.ts`：

```ts
import { useQuery } from '@tanstack/react-query'
import { rawFetch } from '@/api/client'

export type CareerStage = 'exploring' | 'focusing' | 'job_hunting' | 'sprinting'

export function useCareerStage() {
  return useQuery<{ stage: CareerStage }>({
    queryKey: ['career-stage'],
    queryFn: () => rawFetch('/me/stage'),
    staleTime: 5 * 60 * 1000,  // 5 分钟内不重取
  })
}
```

### C.2 首页 `HomePage.tsx` 按阶段切 CTA

在现有首页主按钮逻辑里加一层分支。伪代码：

```tsx
const { data: stageData } = useCareerStage()
const stage = stageData?.stage ?? 'focusing'  // 未加载时兜底为聚焦，避免闪烁

// 第一屏主 CTA
if (stage === 'exploring') {
  return <CTA to="/explore" label="不知道选什么？→ 去对比探索" subtitle="先弄懂几个方向长什么样，再选目标" />
}
// 其它阶段保持当前首页逻辑
```

**交互原则**（来自 Sally）：
- **不显式告诉用户"你处于 X 阶段"**——阶段变化是静默的
- 文案上不出现"阶段""新手""入门"等可能让用户自我归类的词
- 只通过**主按钮指向不同页面**来引导

### C.3 新增 `/explore` 对比探索页

**路由**：`frontend/src/pages/ExplorePage.tsx`

**页面结构**（从上到下）：

```
┌────────────────────────────────────────────┐
│ 对比探索                                     │
│ 并排看两个方向，帮你决定往哪走。              │
├──────────────────┬─────────────────────────┤
│  [左侧：选岗位 ▼]  │  [右侧：选岗位 ▼]        │
│  AI 工程师          │  后端工程师              │
├──────────────────┴─────────────────────────┤
│ 你每天真正在做的事                            │
│  ┌─────────────┐ ┌─────────────┐            │
│  │ 左岗位叙事   │ │ 右岗位叙事   │            │
│  │ 80-120 字   │ │ 80-120 字   │            │
│  └─────────────┘ └─────────────┘            │
├──────────────────────────────────────────┤
│ 什么会耗尽你                                 │
│  ┌─────────────┐ ┌─────────────┐            │
│  │ ...         │ │ ...         │            │
│  └─────────────┘ └─────────────┘            │
├──────────────────────────────────────────┤
│ ... 依次 6 个维度 ...                        │
├──────────────────────────────────────────┤
│  [ 选 AI 工程师作为我的目标 → ]               │
│  [ 选后端工程师作为我的目标 → ]                │
└────────────────────────────────────────────┘
```

**关键设计（Sally 定）**：
- **每个字段的叙事是一段连贯的话**，不是 bullet。像杂志对比专栏
- **不展示薪资、技能列表、zone** —— 这些在 `/role/:id` 已有，对比卡专做叙事层
- **无任何"分数"、"评级"、"雷达图"、"百分比"**
- 视觉语言沿用现有**冷色玻璃**美学，不引入纸质/暖色/杂志风材质。左右栏用轻微的分隔线（`border-slate-200`）区分，不用颜色区块
- 两个"选它"按钮平级，**不暗示哪个更好**
- 叙事字段的 label 用 `text-[11px] uppercase tracking-widest text-slate-500`（小标题标签风格），下面是 `text-[14px] leading-relaxed text-slate-900` 的叙事正文

**组件拆解**：
- `frontend/src/pages/ExplorePage.tsx` — 页面壳，管左右两个 node_id 的状态
- `frontend/src/components/explore/JobPickerButton.tsx` — 点击后展开菜单，列出 5 个 MVP 岗位（其它 node_id 灰色不可选，显示"叙事建设中"）
- `frontend/src/components/explore/ComparisonRow.tsx` — 单行两列对比
- `frontend/src/components/explore/NarrativeColumn.tsx` — 单列叙事内容

**URL 参数**：
- `/explore` → 默认两侧空
- `/explore?left=ai-engineer` → 左侧预选
- `/explore?left=ai-engineer&right=java` → 两侧都预选

### C.4 `/graph` 卡片上增加"对比看看"入口

在 `frontend/src/components/explorer/Coverflow.tsx` 的卡片详情区（或 hover 出现的操作按钮区），加一个轻量的文字链接：

```tsx
<a
  href={`/explore?left=${node.node_id}`}
  className="text-[12px] text-slate-500 hover:text-blue-600"
>
  跟别的方向对比看看 →
</a>
```

只在卡片有 `contextual_narrative` 的 5 个 MVP 岗位上显示。

### C.5 `/role/:id` 底部增加同样入口

`frontend/src/pages/RoleDetailPage.tsx` 页面底部（salary/zone 信息之后），加一个小 section：

```tsx
{data.contextual_narrative && (
  <div className="mt-12 text-center">
    <a
      href={`/explore?left=${data.node_id}`}
      className="text-[13px] font-semibold text-slate-900 border-b-2 border-slate-900 pb-0.5 hover:text-blue-700 hover:border-blue-700"
    >
      对比相似方向 →
    </a>
  </div>
)}
```

### C.6 "选它"按钮行为

点击 `/explore` 页面底部的"选 X 作为我的目标 →" 按钮，应：
1. 调用 `PATCH /profile` 把 `target_node_id` 设成选中的 node_id
2. 跳转到 `/profile`（如果已有画像）或 `/profile/upload`（如果没上传过简历）
3. 后续用户刷新时 `useCareerStage()` 自动返回 `focusing`（因为现在有 target 和 profile 了），首页 CTA 自然切换

---

## Part D：内容工程流程

### D.1 时间线

| 阶段 | 时长 | 产出 |
|---|---|---|
| 写 `scripts/gen_contextual_narrative.py` | 1 小时 | LLM 批量生成脚本 |
| 跑 LLM 草稿（5 岗位） | 10 分钟 | `data/contextual_narrative_draft.json` |
| 人工审改（每岗位 ~2 小时） | 10 小时 | 改到可发布的叙事 |
| 合并回 `graph.json` + sync DB | 30 分钟 | 数据就绪 |
| **合计** | **~12 小时** | |

### D.2 审稿 checklist

每个岗位 6 字段审完之前，逐条核对：

- [ ] `what_you_actually_do` 至少有 2 个具体细节（具体的工具 / 具体的对话 / 具体的时间点）
- [ ] `what_drains_you` 写的是**这个岗位特有的消耗**，不是所有程序员都会有的"加班累"
- [ ] `three_year_outlook` 现在时，不出现"截至 2024 年""未来可能"这种模糊免责词
- [ ] `who_fits` 写性格而非技能，且**明确有"不适合的人"**
- [ ] `ai_impact_today` 具体到任务级别（不是"AI 改变行业"）
- [ ] `common_entry_path` 至少给 2 条路径，其中 1 条是**非大厂路径**
- [ ] 通读：读完能感到**温度**，不像 JD 摘要

---

## 验收标准

### 后端
```bash
# 1. 未登录 → 401
curl http://localhost:8000/me/stage

# 2. 已登录但无 profile → exploring
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/me/stage
# 期望 {"stage": "exploring"}

# 3. 有 profile + target + 1 份报告 + 0 次面试 → focusing
# （手动造数据后测）

# 4. graph.json 5 个 MVP node 的 /graph API 返回 contextual_narrative 非 null
curl http://localhost:8000/graph/nodes | jq '.[] | select(.node_id=="ai-engineer") | .contextual_narrative'
```

### 前端

手动走一遍：

1. **新用户登录**（没 profile）→ 首页主 CTA 是"去对比探索"，跳 `/explore`
2. `/explore` 默认两侧空，点左侧选 AI 工程师、右侧选后端工程师 → 6 行对比渲染正确
3. 点"选 AI 工程师作为我的目标" → 跳 `/profile`，profile 的 target_node_id 已设为 ai-engineer
4. 上传简历后刷新首页 → 主 CTA 变成"生成你的职业发展报告"（因为阶段变 focusing）
5. 去 `/graph` 点 AI 工程师卡片 → 卡片上显示"跟别的方向对比看看 →"，点击跳 `/explore?left=ai-engineer`
6. `/role/ai-engineer` 页面底部有"对比相似方向 →"入口

### 内容

```bash
python -c "
import json
d = json.load(open('data/graph.json', encoding='utf-8'))
mvp = ['java', 'frontend', 'ai-engineer', 'algorithm-engineer', 'data-analyst']
for nid in mvp:
    n = next(x for x in d['nodes'] if x['node_id'] == nid)
    cn = n.get('contextual_narrative')
    if not cn:
        print(f'❌ {nid} 缺 contextual_narrative')
        continue
    missing = [k for k in ['what_you_actually_do','what_drains_you','three_year_outlook','who_fits','ai_impact_today','common_entry_path'] if not cn.get(k)]
    if missing:
        print(f'❌ {nid} 缺字段: {missing}')
    else:
        lengths = {k: len(cn[k]) for k in cn}
        print(f'✅ {nid}: {lengths}')
"
```

期望：5 个 MVP 岗位全部 `✅`，每个字段长度在 60-140 字之间。

---

## 分工建议

| 任务 | 工作量 | 所需技能 | 可否并行 |
|---|---|---|---|
| 后端（服务 + 端点 + API） | 1 人日 | Python/FastAPI | ✅ |
| 前端（/explore 页 + 组件） | 1.5-2 人日 | React/TS + TailwindCSS | ✅（等后端 /me/stage 接口契约） |
| 首页 CTA + 入口链接 | 0.5 人日 | React/TS | 与前端组件并行 |
| LLM 草稿脚本 | 1 小时 | Python + prompt | ✅ |
| **内容审改（5 岗位）** | **10 小时** | **行业理解 + 写作品味** | 与开发并行 |

**内容审改这块不能外包给 LLM**——LLM 的温和正面倾向和"截至 XXXX 年"的免责条款会毁掉 70% 的叙事价值。必须由懂行业的人逐条审。如果你自己没时间，找一个实习过 2 个以上岗位的学长学姐、或者有意识观察过行业的 PM 做这件事。

---

## 完成后的交付物

```
新增：
  docs/career-stage-and-explore-spec.md         (本文件)
  backend/services/career_stage.py               (新服务)
  frontend/src/hooks/useCareerStage.ts           (新 hook)
  frontend/src/pages/ExplorePage.tsx             (新页面)
  frontend/src/components/explore/*.tsx          (4 个新组件)
  scripts/gen_contextual_narrative.py            (LLM 草稿脚本)

修改：
  data/graph.json                                (5 个 node 补 contextual_narrative)
  backend/routers/graph.py                       (透出 contextual_narrative)
  backend/routers/user.py (或 profiles.py)       (新增 /me/stage)
  frontend/src/pages/HomePage.tsx                (按阶段切 CTA)
  frontend/src/pages/RoleDetailPage.tsx          (底部加对比入口)
  frontend/src/components/explorer/Coverflow.tsx (卡片加对比链接)

数据库：
  无 schema 变更。sync_graph_to_db 照跑，叙事内容只在 graph.json 里。
```

## 关键提示（交给组员前再读一遍）

- **先跑通阶段判定和对比卡渲染，再写内容**。这样内容写好直接能看效果，心理反馈闭环快
- **不要在阶段逻辑里写 "新手/老手/入门/高手" 这种词**——阶段是内部状态，用户看不到
- **不要动 `/report` 报告生成链路**——这不是这个 spec 的范围
- **对比卡里严禁出现分数、进度条、雷达图**——liu 在项目 memory 里明确反对
- **叙事字段的渲染用 `whiteSpace: normal`**，不要沿用 PDF 那种 `whiteSpace: pre`（这里是常规段落，不是手动排版）
- **5 个 MVP 之外的节点**在 `/explore` 的 picker 里**显示为灰色 + "叙事建设中"** 提示，不要让用户以为它们也能对比
- **内容里严禁出现"截至 2024/2025/2026 年"、"根据近期数据"、"过去三年"这种免责句式**——liu 明确要求教练语气实时感，直接说"今天 AI 已经能…"、"这个岗位现在正在…"
