# 职途智析 — 系统架构与技术实现细节

> 用于竞赛 PPT 素材整理。涵盖数据来源、算法设计、架构决策及创新点。

---

## 一、系统定位

面向计算机专业大三/大四学生的 AI 职业规划系统。核心能力：
- 能力画像构建（简历解析 → 技能提取）
- 岗位方向推荐（技能匹配 + 意愿匹配）
- JD 诊断（匹配度 + 缺口分析 + 准备度评估）
- AI 多角色成长教练（7 个专职 agent）
- 学习路径规划（基于 developer-roadmap）
- AI 替代风险评估（基于真实市场数据）

---

## 二、数据来源与处理

### 2.1 岗位图谱数据

| 数据源 | 数据量 | 用途 |
|--------|--------|------|
| 智联招聘 2016-2025 | 13GB / 1332 万条 JD | 提取岗位节点、技能要求、薪资中位数 |
| O*NET 职业数据库 | 1016 个职业 × 8 维度 | AI 替代压力计算、任务自动化概率 |
| developer-roadmap | 83 个技术路线图 | 学习路径结构化数据 |

### 2.2 图谱规模

- **40 个 CS 岗位节点**：覆盖前端/后端/AI/数据/安全/游戏/运维等 18 个方向
- **585 条关联边**：岗位间转型路径（由 Claude AI 审核，72% 通过率）
- **4 个安全区域**：safe(13) / thrive(19) / transition(7) / danger(1)

### 2.3 每个岗位节点包含的字段（19 个）

| 字段 | 来源 | 说明 |
|------|------|------|
| `node_id` / `label` | 智联招聘 JD 聚类 | 岗位标识和中文名 |
| `role_family` | 手动分类 | 所属方向（18 类） |
| `must_skills` | JD 技能提取 + LLM 净化 | 核心技能列表 |
| `description` | LLM 生成 | 岗位简介 |
| `core_tasks` | LLM 生成 | 日常工作内容（5-6 项） |
| `promotion_path` | LLM 生成 | 晋升路线（5 级） |
| `replacement_pressure` | O*NET 自动化概率 + 市场信号 | AI 替代压力（0-100） |
| `human_ai_leverage` | 计算得出 | 人类杠杆值（AI 增强人类能力的程度） |
| `zone` | 基于 replacement_pressure 阈值 | 安全区划分 |
| `routine_score` | O*NET 任务数据 | 工作重复度 |
| `career_level` | LLM 判断 | 职级（2=初中级, 4=架构, 5=管理） |
| `soft_skills` | LLM 评估 | 5 维软技能要求 |
| `salary_p50` | 智联招聘统计 | 薪资中位数 |
| `onet_codes` | 手动映射 | O*NET 职业代码 |
| `related_majors` | LLM 推断 | 相关专业 |

### 2.4 AI 替代压力计算方法

```
replacement_pressure = 
    O*NET 任务自动化概率加权平均 × (1 + market_modifier)

market_modifier = 
    近 3 年 AI 工具在该岗位 JD 中出现频率的变化率（±15%）
    数据源：151 条市场信号（8 年 × 20 个方向）
```

关键发现：data_science 方向 AI 渗透率 2023→2024 暴增 10 倍（1.12%→11.59%）

---

## 三、技能匹配算法

### 3.1 三层匹配架构

```
用户技能列表
    │
    ├── Tier 1: 精确匹配（字符串相等，case-insensitive）
    │   结果：overlap_skills / missing_skills
    │
    ├── Tier 2: 语义匹配（embedding cosine similarity ≥ 0.70）
    │   模型：DashScope text-embedding-v3（1024 维）
    │   示例：MySQL ↔ SQL（0.72）、React ↔ JavaScript（0.75）
    │   缓存：data/skill_embeddings.json（首次调用后持久化）
    │
    └── 最终得分 = 精确匹配数 + 语义匹配数 × 0.7
```

### 3.2 JD 诊断四维度匹配

| 维度 | 权重 | 说明 |
|------|------|------|
| 技术技能匹配 | 40% | JD 要求 vs 用户画像技能 |
| 发展潜力 | 20% | 学习能力、项目经验丰富度 |
| 基本要求 | 15% | 学历、经验年限 |
| 软技能/素质 | 25% | 沟通、团队协作、抗压等 |

### 3.3 准备度（Readiness %）

```
准备度 = 已匹配技能数 / (已匹配 + 缺口) × 100%
```

展示策略（参考 LinkedIn Career Explorer）：
- 先肯定："已具备 8 项核心技能"
- 再引导："再补 3 项即可达标"
- 给行动："优先补 cmake、gdb"

---

## 四、多 Agent 架构

### 4.1 整体架构（纯路由器模式）

```
用户消息
    │
    ├── Tier 1: Regex 快速路径（确认语/JD文本/搜索词/迷茫表达）
    ├── Tier 2: Semantic Router（embedding 相似度匹配，10/10 准确率）
    └── Tier 3: LLM 分类器（兜底，DashScope qwen-plus）
    │
    ↓ 纯路由（不生成回复）
    │
    ├── 智析教练（coach_agent）— 闲聊/情绪/引导/职业讨论
    ├── 方向顾问（navigator）— 岗位推荐/图谱探索/转型路径
    ├── 匹配分析师（jd_agent）— JD 诊断匹配度
    ├── 画像顾问（profile_agent）— 画像查看/分析
    ├── 面试教练（practice_agent）— 面试题练习
    ├── 成长顾问（growth_agent）— 学习进度/成长数据
    └── 报告分析师（report_agent）— 生成报告
```

### 4.2 架构设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 路由器是否聊天 | 不聊天（纯分类） | 参考 OpenAI Swarm / AutoGen GroupChat：路由和聊天分离，职责单一 |
| 意图分类方式 | 三层级联 | regex(0延迟) → semantic(亚秒) → LLM(兜底)，准确率和延迟平衡 |
| 确认语处理 | 路由回上一个 agent | 参考 OpenAI Swarm 的 `response.agent` 机制 |
| 数据隔离 | triage 看摘要，agent 看完整数据 | 防止路由器用上下文编造数据 |
| Agent 间上下文 | [调用背景] 注入 | 被调用 agent 知道为什么被调用 |

### 4.3 Semantic Router 技术细节

- 库：semantic-router 0.1.12
- Encoder：DashScope text-embedding-v3（通过 OpenAI 兼容接口）
- 路由数：8 条（7 个 agent + 搜索 JD）
- 每条路由：8-10 条中文示例话术
- 分类延迟：单次 embedding API 调用（~200ms）
- 初始化：首次启动时 embedding 所有示例（~15 秒），之后使用 LocalIndex 内存缓存

### 4.4 SSE 流式输出

```
POST /api/chat → SSE stream
  ├── data: {"session_id": 42}           — 会话 ID
  ├── data: {"agent": "navigator"}       — 当前响应的 agent
  ├── data: {"content": "你的C++..."}    — 流式文本
  ├── data: {"jd_cards": [...]}          — JD 搜索结果卡片
  ├── data: {"card": {"type":"jd_diagnosis","id":1}} — 诊断报告卡片
  └── data: [DONE]
```

---

## 五、功能模块清单

### 5.1 能力画像
- 简历上传（PDF/DOC）→ LLM 提取技能/教育/项目/经历
- 自动定位到图谱节点（LLM 匹配最佳岗位）
- 画像质量评分
- 系统推荐岗位（技能匹配 + 即将加入意愿匹配）

### 5.2 岗位图谱
- Coverflow 3D 卡片浏览器 + 区域过滤
- 岗位对比（当前 vs 目标，gap radar）
- 目标设定 → 缺口技能列表 → 学习路径入口
- AI 替代压力可视化

### 5.3 成长教练（7 角色）
- 会话保存/继续/历史列表/LLM 自动标题
- 页面感知（知道用户在哪个页面）
- 主动触发（简历上传/目标设定后自动发起对话）
- 跨会话教练备忘录（LLM 提取关键信息）
- 真实 JD 搜索（Tavily API + 三层过滤）
- JD 搜索结果卡片 + 一键诊断
- 语音输入/输出（浏览器 STT/TTS）

### 5.4 JD 诊断
- 四维度匹配分析
- 结构化报告页（准备度进度条 + 已具备技能 + 缺口优先级）
- 诊断后行动引导（练面试题/搜类似/看学习路径）

### 5.5 学习路径
- 基于 developer-roadmap 83 个路线图
- 按目标岗位自动匹配路线图
- 子主题进度追踪（checkbox）
- 技能掌握确认 → 自动更新画像 + 匹配度

### 5.6 首页
- 冷启动：编辑式 hero + 上传 CTA
- 返回用户：画像卡 + 指标 + 旅程引导 + 活动热力图
- 旅程引导卡：根据用户阶段动态显示下一步

---

## 六、技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 19 + TypeScript + Tailwind CSS 4 + Framer Motion |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| AI 框架 | LangGraph（StateGraph + Swarm handoff） |
| LLM | DashScope（qwen-plus / qwen-max） |
| Embedding | DashScope text-embedding-v3（1024 维） |
| 向量数据库 | Qdrant |
| 意图路由 | semantic-router + regex + LLM fallback |
| JD 搜索 | Tavily API |
| 语音 | 浏览器原生 Web Speech API（STT/TTS） |

---

## 七、创新点总结

1. **三层意图路由**：regex → semantic embedding → LLM，兼顾准确率和延迟
2. **纯路由器 + 多角色 Agent**：参考 OpenAI Swarm，路由器不聊天，7 个专职角色各司其职
3. **语义技能匹配**：不只是字符串比较，embedding 余弦相似度识别关联技能
4. **准备度（Readiness %）**：参考 LinkedIn Career Explorer，从"你缺什么"变成"你已经准备好多少"
5. **真实市场数据驱动的 AI 替代评估**：基于 13GB 智联招聘 + O*NET + 151 条市场趋势信号
6. **教练备忘录**：跨会话记忆，LLM 提取用户关键信息，持续个性化
7. **就业意愿分析**（实施中）：不只匹配能力，同时匹配用户偏好和价值取向

---

## 八、待实现功能

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 就业意愿问卷 | P0 | 选题明确要求，画像页内嵌 5-6 题 |
| 结构化职业规划报告 | P0 | 带时间线的行动计划（短/中/长期） |
| AI 替代叙事强化 | P1 | 图谱/推荐/报告中强化 AI 影响分析 |
| 成长看板重定位 | P1 | 从"练习次数"改为"闭环进度" |
| 求职追踪融入主链路 | P1 | 面试后触发教练复盘 |
| O*NET importance/level | P2 | 技能从二元判断到程度化评估 |
