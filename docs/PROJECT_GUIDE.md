# 职途智析 · 项目详解与使用指南

> 这份文档写给两类人读：
> - **开发者 / 评委**：想知道系统底层是怎么工作的、架构决策背后的逻辑
> - **学生用户**：想知道怎么一步步把这个系统用好

---

## 目录

1. [产品形态一览](#产品形态一览)
2. [系统架构](#系统架构)
3. [数据资产](#数据资产)
4. [核心模块详解](#核心模块详解)
5. [学生使用流程（推荐路径）](#学生使用流程推荐路径)
6. [设计决策记录](#设计决策记录)
7. [常见问题](#常见问题)

---

## 产品形态一览

**职途智析**是一个面向中国 CS/IT 大学生的 AI 职业规划助手。学生通过上传简历 + 和 AI 教练对话，系统会持续追踪学生成长、给出方向对齐分析、生成个性化职业发展报告。

**核心闭环**：

```
上传简历 → 建立画像 → 选定目标岗位 → JD 诊断找缺口
                ↓
        记录项目 / 投递 / 面试（成长档案）
                ↓
        生成 AI 发展报告（综合评价 + 对齐 + 补法路径）
                ↓
        档案精修（学生自补空洞项目）→ 下一次报告通过
                ↓
              回到"更新档案 → 再生成报告"
```

---

## 系统架构

### 三层分工

```
┌─────────────────────────────────────────────────────────────┐
│ 前端 React（localhost:5173）                                │
│  · Layout + ChatPanel（右侧常驻 AI 教练）                     │
│  · 页面：画像 / 图谱 / 报告 / 成长档案 / 角色详情              │
└─────────────────────────────────────────────────────────────┘
                        ↓ REST / SSE
┌─────────────────────────────────────────────────────────────┐
│ 后端 FastAPI（localhost:8000）                               │
│  · Routers：HTTP 层（profiles / report / jd / growth-log...）│
│  · Services：业务逻辑（report_service / jd_service ...）      │
│  · DB：SQLite + SQLAlchemy ORM                               │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ AI Agent 层（LangGraph）                                     │
│  · Supervisor：意图识别 + 路由                                │
│  · 专家 Agent：navigator / growth / profile / coach / jd     │
│  · Tools：每个 Agent 绑定领域工具集                           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ LLM + 向量层                                                 │
│  · 阿里云百炼（qwen-turbo / qwen-plus）                       │
│  · text-embedding-v3（语义向量）                              │
│  · Qdrant（可选，默认嵌入式）                                  │
└─────────────────────────────────────────────────────────────┘
```

### Agent 体系（LangGraph）

**Supervisor Pattern**：用户一句话进来 → Supervisor 识别意图 → 路由到合适的专家 Agent → Agent 调用工具 → 返回结果。

| Agent | 职责 | 典型工具 |
|-------|------|---------|
| `navigator` | 岗位图谱探索 | `search_nodes` / `get_promotion_path` / `compare_roles` |
| `growth` | 成长档案追踪 | `get_project_progress` / `get_interview_records` |
| `profile` | 画像诊断 | `get_profile_summary` / `locate_on_graph` |
| `coach` | 教练对话 | 综合信息 + LLM 推理 |
| `jd` | JD 诊断 | `diagnose_jd` |
| `search` | 网络搜索 | `web_search` |

---

## 数据资产

### `data/graph.json` · 岗位图谱（45 节点）

**每个节点包含**：
- 基础信息：`node_id` / `label` / `role_family` / `zone` / `career_level`
- 技能分层：`skill_tiers.core / important / bonus`（每项带 `name` + `freq`）
- 晋升路径：`promotion_path`（从 L1 到 L5 的典型路径）
- 软技能要求：`soft_skills`（通用岗位要求维度）
- **curated 叙事字段**（v2 起启用）：
  - `project_recommendations`：3 个典型实战项目 + why 说明
  - `differentiation_advice`：如何与同行拉开差距
  - `ai_impact_narrative`：AI 对该岗位的影响分析
- 市场指标：`replacement_pressure` / `human_ai_leverage` / `salary_p50`

### `data/market_signals.json` · 市场信号

按 `role_family` 归组的需求变化、薪资走势、时机判断。

### `data/skill_fill_path_tags.json` · 技能补法路径分类

```json
{
  "数据结构": "learn",
  "高并发": "practice",
  "Docker": "both"
}
```

- `learn` — 概念/理论类，靠系统学习
- `practice` — 系统工程类，靠做项目
- `both` — 工具/框架类，先学后做

---

## 核心模块详解

### 1. 能力画像（Profile）

**入口**：`/profile`

**流程**：
1. 上传简历（PDF/图片/文字粘贴）→ LLM 提取结构化数据
2. 自动运行 SJT 情景判断题 → 软技能评估
3. `profile_service.locate_on_graph()` 用 IDF 加权计算学生在 45 节点图谱上的最佳坐标
4. 输出：技能列表 / 项目经历 / 教育背景 / 软技能雷达 / 推荐岗位

**关键接口**：
- `GET /api/profiles/me` — 获取当前用户画像
- `POST /api/profiles` — 上传/更新画像
- `PATCH /api/profiles/me/projects/refine` — 按内容匹配更新简历项目描述（用于档案精修）
- `POST /api/profiles/sjt/generate` + `/sjt/submit` — SJT 测评

---

### 2. 岗位图谱（Graph）

**入口**：`/graph`

**设计思想**：不用大表列 JD，而用**可视化图谱 + 邻域推荐**。学生点击一个岗位节点 → 看到该岗位完整信息 + 邻近岗位（转型参考）。

**关键页面**：
- `/graph` · 全图探索（@xyflow/react 交互）
- `/roles/:id` · 单岗位详情（技能要求、晋升路径、AI 影响、典型项目）

---

### 3. JD 诊断

**入口**：右侧 ChatPanel 粘贴 JD，或 `/growth-log` 的诊断入口

**流程**：
1. 学生粘贴一份真实 JD → 后端抽取目标技能 + 岗位要求
2. 和学生画像比对 → 输出：
   - 四维分（基础 / 职业技能 / 职业素养 / 发展潜力）
   - 匹配度百分比
   - 技能差距清单 + `top_missing`
3. 保存为 `JDDiagnosis` 记录 → 报告生成时复用

**评分原则**（见 `jd_service.py` prompt）：
- 拒绝因"标签数量多"就给高分
- 要求 detail 字段引用具体证据
- 空白画像有基准分上限

---

### 4. 成长档案（Growth Log）

**入口**：`/growth-log`

**三个 Tab**：

#### (a) `filter=project` · 项目追踪
记录学生做过 / 正在做的项目。每条 `ProjectRecord` 含名称、描述、使用技能、状态（进行中/已完成）。

#### (b) `filter=pursuit` · 求职追踪
记录 JD 投递 → 筛选 → 面试 → 复盘全流程。每条 `JobApplication` 含公司、职位、状态、时间线、反思。

#### (c) `filter=refine` · 档案精修（核心创新）
**设计哲学**：AI 识别差距、展示格式，**学生必须用真实数据填空**。

- 系统扫描学生简历 + 成长档案的项目描述
- `_diagnose_profile()` 识别 4 类"空洞模式"：
  - 缺数字（无量化数据）
  - 缺成果（无具体产出）
  - 过于简短（<30 字）
  - 只说"参与"未说明"负责"
- 每条待完善项目展示：**现在的样子**（原文灰字版）+ **让它更亮**（差距列表）+ **别人怎么写**（参考格式）+ **你来写**（空 textarea）
- 学生提交时，前端做软校验（必须含数字 + 长度 + 动词），**不达标按钮禁用**
- 保存成功后卡片 3 秒"已焕新"动效 → 淡出
- 下一次报告生成时，该项目会显示"通过"

**前端组件**：`frontend/src/components/growth-log/RefineSection.tsx`

---

### 5. AI 发展报告（Report）

**入口**：`/report` · 点击"生成新报告"按钮

**报告章节顺序**（v2 最新）：

```
1. AI 综合评价
   · LLM 生成的 200-300 字叙事段落
   · 引用真实项目细节（不说套话）
   · 严禁罗列分数、禁止时间表预测

2. Hero 区
   · 目标岗位名
   · 核心技能覆盖率事实陈述（X/Y 覆盖 · Z 个有项目证据）
   · 琥珀色项目推荐卡片（2-3 张，来自 graph.json curated）
   · 每张卡片含：项目名 + why + "可覆盖缺口"标签
   · ScoreRing（匹配分）降级到右上角小字
   · 数据错配时显示诚实话术 + differentiation_advice

3. 方向对齐分析（CareerAlignment）
   · LLM 基于学生技能/项目/软技能生成
   · 绑定 graph.json 节点（防幻觉）
   · 每条对齐带 evidence + gap
   · 显式列出"无法判断的"维度

4. 市场竞争力分析（三段式补法路径地图）
   · 📚 需要系统学习的概念（slate 色系）
   · 🛠️ 需要项目实践才能掌握（amber 色系）
   · 🔀 先学后做（violet 色系）
   · 底部诚实统计：N 个缺口 · X 个可通过项目补 · (N-X) 个需学习

5. 档案体检（Diagnosis）
   · 识别空洞项目描述
   · 提供"去补充"按钮 → 跳转成长档案精修 Tab

6. 个性化成长计划（Action Plan）
   · 三阶段：立即整理（0-2周）/ 技能补强（2-6周）/ 项目冲刺+求职（6-12周）
   · 每条任务带 deliverable
   · 自动从成长档案新增记录时勾选完成

7. AI 影响与护城河
   · 位于报告末尾
   · 展示 graph 节点的 ai_impact_narrative + differentiation_advice
   · 长文本展开/收起
```

**关键机制**：
- **Delta 对比**：每份新报告会和上一份对比，展示"进步 / 待提升 / 下一步"
- **项目-缺口匹配**：后端用 embedding 预计算 `covered_skills`（阈值 0.55）
- **错配护栏**：当所有项目推荐都无法覆盖学生缺口时，触发 `project_mismatch` 分支，展示诚实话术
- **一键导出**：右上角按钮调用 `window.print()`，利用 `@media print` CSS 样式

---

### 6. AI 教练（Chat Panel）

**位置**：右侧常驻，所有页面可用

**能做什么**：
- 自然语言提问（"我该先补哪个技能？"）
- 粘贴 JD 触发诊断
- 根据当前路由显示 Context Tip（例如在画像页提示"试试 JD 诊断"）
- 支持语音（浏览器 TTS + STT）

**底层路由**：`backend/routers/chat.py` → `agent/supervisor.py` → 识别意图分发到专家 Agent

---

## 学生使用流程（推荐路径）

### 第一次打开（0-10 分钟）

1. **注册/登录** → `/login`
2. **上传简历** → `/profile` 页点"上传简历"（PDF 或图片）
3. **完成 SJT** → 约 10 题情景判断题，系统评估软技能维度
4. **看画像摘要** → 系统自动定位你在图谱上的坐标 + 推荐相近岗位

### 第一次生成报告（10-15 分钟）

5. **选择目标岗位** → `/graph` 页点击你感兴趣的岗位节点 → 标为"目标"
6. **粘贴一份真实 JD** → 右侧教练输入 JD → 获得 JD 诊断（四维分 + 技能缺口）
7. **点"生成报告"** → `/report` 页生成第一份完整发展报告

### 持续成长（每周一次）

8. **补充项目** → `/growth-log?tab=projects` 记录你这周做的事
9. **查看档案精修** → 系统发现空洞项目描述 → 点"去补充" → 用真实数据补写
10. **更新报告** → 回 `/report` 点"更新报告" → 新报告展示 Delta 变化

### 求职阶段（投递后）

11. **记录投递** → `/growth-log?tab=pursuits` 记录公司、职位、状态
12. **面试复盘** → 每轮面试后用 AI 复盘生成面试反思
13. **Coach 对齐** → 遇到具体问题时直接问教练（"XX 公司这个岗位要不要投？"）

---

## 设计决策记录

### 为什么不做"senior/mid/junior"定位？

**历史**：v1 有 `positioning_level` 字段，按 `core_pct >= 80 → senior / >= 50 → mid / else junior` 分类。

**问题**：简历 + 项目数据**根本无法测量熟练度**。一个学生把简历技能栏写满，系统会给出 senior 标签 —— 但他可能连一个项目实证都没有。

**决策**（已执行）：**彻底删除** `positioning_level` 字段 + 前端"你在这里"标记。报告里只展示**事实陈述**（X/Y 覆盖 · N 个项目证据）。

### 为什么"方向对齐分析"由 LLM 生成而不是规则匹配？

**规则匹配的问题**：分类器 → 职业标签 = 和 positioning_level 同源的虚假精确。

**LLM 分析的好处**：LLM 可以做语义推理（"你有 Redis + Kafka → 中间件方向对齐度高"），而且可以显式说"无法判断的维度"。

**防幻觉护栏**：
- LLM 输出的 `node_id` **必须**在 `graph.json` 里存在，不存在的过滤掉
- 每条 alignment **必须**引用学生具体数据作为 evidence
- 保守的 embedding 阈值（候选预选 top 15 → LLM 只能从里面选）

### 为什么报告末尾才放 AI 影响卡片？

早期版本放在 SkillGap 和 ActionPlan 中间 —— **打断学生行动心流**（看到缺口 → 项目补齐 → 行动计划是连续叙事，不该被"AI 冲击"这种存在主义话题打断）。

现在放末尾 —— 学生读完行动计划后再看"长期 AI 参照"，顺序合理。

### 为什么缺口要分三类（learn/practice/both）？

**本源问题**：不是所有技能都该靠项目补。
- 数据结构 / 操作系统 / 算法 → 靠系统学习更高效
- 高并发 / 分布式 / 性能优化 → 靠做项目才能掌握
- Docker / K8s / Git → 先学后做

把所有缺口塞进"项目能不能覆盖"的二元框里是错误抽象，会误导学生。三段式补法地图让学生看到**每个缺口的最佳出路**。

### 为什么档案精修不让 AI 代写？

**AI 代写的坏处**：
1. 学生拿到一份编得漂亮但不属于自己的简历
2. 面试被问细节立刻穿帮
3. 学生错过"强迫自我反思"的成长机会

**我们的做法**：
- AI 只指出差距（"缺量化数字"、"只说参与没说负责"）
- AI 给格式范本（"参考：实现了 XX，QPS 从 Y 提升到 Z"）
- 学生**必须**用自己真实数据填空
- 前端硬校验：必须含数字 + 长度 >= 30 + 含动词（负责/主导/实现）

---

## 常见问题

### Q: 为什么报告生成需要等 30-60 秒？

报告生成涉及多次 LLM 调用：
- 综合评价叙事（qwen-turbo · 含学生项目 context）
- 方向对齐分析（qwen-plus · 绑定 graph 节点）
- 隐式技能推断（推断 C++ 项目隐含的 STL/Linux）
- Embedding 批量计算（项目 vs 缺口的相似度）

每次 LLM 调用 10-30 秒不等，合计 30-60 秒正常。有重试机制（首次 60s 超时，失败再 90s）。

### Q: "职业发展路径"模块显示"还需要更多数据"怎么办？

说明当前画像**项目数 < 2** 或 **技能数 < 5**。解决：
1. `/profile` 补充简历项目
2. `/growth-log?tab=projects` 记录至少 2 个项目（含描述数字）
3. 回报告页点"更新报告"

### Q: 档案精修保存后，为什么下次报告还说这个项目空洞？

两种可能：
1. 你补的内容仍然不含数字 / < 30 字 / 没有动词（但前端校验应该拦下了，若发生请报 bug）
2. 后端 `_diagnose_profile` 规则更严 —— 检查是否真的回答了 evidence

### Q: "Linux / STL 未验证" 被误判怎么办？

v2 已修复：新增 `_infer_implicit_skills_llm()` 让 LLM 推理"C++ 网络库项目必然用 STL + Linux socket" —— 隐式技能会被提升到 `practiced`，不再误判为 claimed 风险。

### Q: 能不能把本项目部署到公网？

技术上可以（FastAPI + React 都是标准 web 技术栈）。**但注意**：
- `.env` 里的 `DASHSCOPE_API_KEY` 不要提交到公网仓库
- SQLite 单机部署足够竞赛 demo；真要上线建议迁 PostgreSQL
- 前端 `API_BASE` 需要改成公网后端地址

### Q: 可以引用其他大模型吗（除了阿里云百炼）？

`backend/llm.py` 支持 `OPENAI_API_KEY` + 自定义 `LLM_BASE_URL` 作为 fallback。理论上兼容 OpenAI API 格式的服务都可以接入。但 `text-embedding-v3` 是阿里云专属，换模型需要同步换 embedding 接口。

---

## 🔧 开发调试小技巧

### 查看后端日志
```bash
python -m uvicorn backend.app:app --reload --log-level debug
```

### 重置数据库
```bash
# 警告：会清空所有用户数据
rm career_planning.db career_planner.db
python -c "from backend.app import create_app; create_app()"  # 自动重建表
```

### 前端 HMR 不工作？
```bash
cd frontend
rm -rf node_modules .vite
npm install
npm run dev
```

### LLM 调用超时？
- 先确认 `DASHSCOPE_API_KEY` 有效（在 [dashscope.aliyun.com](https://dashscope.aliyun.com/) 控制台查用量）
- `report_service.py` 里 narrative 已配重试（60s → 90s），其他 LLM 调用统一 90s 超时

---

## 📖 进一步阅读

- [README.md](../README.md) · 项目总览 + 快速开始
- [career-alignment-spec.md](career-alignment-spec.md) · LLM 对齐分析完整规范
- [report-hero-redesign-spec-v2.md](report-hero-redesign-spec-v2.md) · Hero 区重构（三段式补法地图）
- [archive-refinement-spec.md](archive-refinement-spec.md) · 档案精修模块规范

---

**本项目为 "基于 AI 的大学生职业规划智能体" 竞赛作品，持续演进中。**
