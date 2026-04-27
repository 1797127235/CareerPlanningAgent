# 职途智析 · AI 大学生职业规划智能体

> 基于大模型的个性化职业发展助手 —— 从简历解析到岗位对齐、从技能诊断到成长追踪，全链路帮中国 CS/IT 学生把"学了什么"转化为"能去哪里"。

---

## ✨ 核心特性

| 模块 | 能做什么 |
|------|---------|
| 🎯 **能力画像** | 上传简历自动解析 → 提炼技能/项目/经历 → SJT 软技能评估 → 在职业图谱上定位你的坐标 |
| 🗺️ **岗位图谱** | 45 个真实 IT 岗位节点 + 可视化探索 + 每个岗位含核心技能、典型实战项目、AI 影响、差异化建议 |
| 🔍 **JD 诊断** | 粘贴任意真实 JD → 四维评分（基础/技能/素养/潜力）+ 技能缺口分析 + **AI 影响分析（AEI 数据）** + **推荐转岗路线** + 可落地成长建议 |
| 📈 **成长档案** | 项目追踪（记录你做过什么）+ 求职追踪（记录投递进度）+ 档案精修（学生自补空洞项目描述） |
| 📊 **AI 发展报告** | 综合评价 · 技能覆盖 · 方向对齐（LLM 分析）· 补法路径地图 · 成长计划 · AI 影响参照 |
| 💬 **AI 教练** | 右侧常驻对话面板 · 结合你当前画像/档案实时给建议 · 支持 JD 诊断、目标对齐、面试准备 |
| 🎤 **AI 模拟面试** | **6 个方向 Skill 驱动出题**（C++/前端/Java/算法/产品/测试）· 画像联动（成长项目/gap 技能/报告结论注入 prompt）· 历史弱项自动复习 · **自定义题量/题型占比** · 空答案强制 0 分 · 多维度评估 |

---

## 🚀 快速开始

### 前置条件

- Python 3.10+
- Node.js 18+
- 一个[阿里云百炼 API Key](https://dashscope.aliyun.com/)（必需）

### 环境变量

复制 `.env.example` 为 `.env`，至少配置：

```bash
DASHSCOPE_API_KEY=sk-your-dashscope-api-key-here
```

### 启动服务

**一键启动（推荐）**
```bash
start.bat   # 按提示选 1 启动前端+后端
```

**手动启动（两个终端）**：

```bash
# 终端 1：后端（端口 8000）
python -m uvicorn backend.app:app --reload

# 终端 2：前端（端口 5174）
cd frontend-v2
npm install
npm run dev
```

浏览器打开 [http://localhost:5174](http://localhost:5174) 开始使用。

---

## 🧰 技术栈

### 后端
- **FastAPI** · 异步 API 框架
- **SQLAlchemy** + **SQLite** · ORM + 轻量数据库
- **LangGraph** · 多 Agent 编排框架
- **阿里云百炼**（qwen 系列）· 大模型推理
- **text-embedding-v4** · 语义向量计算
- **Qdrant** · 向量数据库（可选，默认嵌入式）

### 前端
- **React 19** + **TypeScript** · UI 框架
- **Vite 8** + **Rolldown** · 构建工具
- **TanStack Query** · 服务端状态管理
- **Tailwind CSS 4** · 样式系统
- **Framer Motion** · 动效
- **Recharts** + **@xyflow/react** · 图表 + 图谱可视化
- **Lucide Icons** · SVG 图标库

### AI Agent 架构
- **Supervisor Pattern** · 中央调度器（`agent/supervisor.py`）根据意图路由到专门 Agent
- **6 个专家 Agent**：`navigator`（图谱探索）/ `growth`（成长追踪）/ `profile`（画像诊断）/ `coach`（教练对话）/ `jd`（JD 诊断）/ `search`（网络搜索）
- **Tool 层**：每个 Agent 绑定领域工具集；`coach_agent` 额外装载 pull-based context tools（`get_user_profile` / `get_career_goal` / `get_market_signal` / `get_memory_recall`）按需查询用户状态，避免 SystemMessage 全量 push
- **Skill 系统（coach 专用）** · 基于 Anthropic Skill 规范（`agent/skills/coach-*/SKILL.md`），采用 **Progressive Disclosure 模式**：catalog（15 skill 的 name + description）注入 SystemMessage（~830 tokens），LLM 判断场景后调 `load_skill(name)` tool 按需加载完整规则 —— 相比全量 push 节省 ≥ 60% token，扩到 20 skill 也只吃 ~800 tokens base cost
- **15 个 coach skill** 覆盖大学生职业规划对话场景：`greeting` / `confirmation` / `concern-direct` / `emotional-support` / `comparison-detox` / `direction-scaffold` / `exploring-guide` / `profile-builder` / `progress-report` / `interview-prep` / `resume-review` / `market-signal` / `request-deliver` / `project-planning` / `decision-socratic`

---

## 📂 项目结构

```
CareerPlanningAgent/
├── backend/                    # FastAPI 后端
│   ├── app.py                  # 应用入口 + 路由注册
│   ├── db.py / db_models.py    # SQLAlchemy ORM
│   ├── routers/                # HTTP 路由层
│   │   ├── profiles.py         # 画像 CRUD + 简历解析
│   │   ├── jd.py               # JD 诊断
│   │   ├── report.py           # 职业发展报告生成
│   │   ├── interview.py        # 模拟面试（方向 Skill 驱动 + 画像联动 + 题库缓存）
│   │   ├── growth_log.py       # 成长档案
│   │   ├── applications.py     # 求职追踪
│   │   ├── chat.py             # AI 教练对话
│   │   └── graph.py            # 岗位图谱 API
│   ├── skills/                 # 后端 Skill 池（LLM prompt 模板）
│   │   ├── mock-interview-gen/ #   · 模拟面试题目生成（fallback）
│   │   ├── mock-interview-eval/#   · 模拟面试评估（多维度评分）
│   │   └── ...                 #   · 报告生成、市场叙事等 Skill
│   └── services/               # 业务逻辑层
│       ├── report/             # 报告生成 Pipeline（6 个 Skill 并发）
│       ├── jd_service.py       # JD 诊断核心
│       ├── interview_skill_loader.py  # 面试 Skill 配置加载 + prompt 构建
│       └── dashboard_service.py
├── agent/                      # LangGraph 多 Agent
│   ├── supervisor.py           # 中央调度器 + agent-aware context builder
│   ├── intent_router.py        # 语义意图识别
│   ├── agents/                 # 6 个专家 Agent 实现
│   ├── tools/                  # Agent 工具集（含 coach_context_tools 等）
│   └── skills/                 # Anthropic Skill 规范的 coach skill 池
│       ├── loader.py           #   · Progressive Disclosure loader（catalog + load_full）
│       └── coach-<scenario>/   #   · 每个场景独立目录 + SKILL.md（当前 13 个）
├── backend/interview_skills/   # 面试方向 Skill 体系（按技术方向组织）
│   ├── cpp-system-dev/         #   · C++ 系统开发方向
│   ├── frontend-dev/           #   · 前端开发方向
│   ├── java-backend/           #   · Java 后端方向
│   ├── algorithm/              #   · 算法工程师方向
│   ├── product-manager/        #   · 产品经理方向
│   ├── test-development/       #   · 测试开发方向
│   ├── _shared/
│   │   └── references/         #       方向共享参考知识库（知识点清单）
│   └── ...                     #   · 逐步扩充
├── frontend-v2/                # React 前端（Vite 8）
│   └── src/
│       ├── pages/              # 17 个路由级页面
│       ├── components/         # 可复用组件（coach-v2 / editorial / growth-log / ui 等）
│       ├── api/                # HTTP 客户端（14 个模块）
│       ├── hooks/              # React hooks（12 个）
│       └── lib/                # 工具函数
├── data/
│   ├── graph.json              # 岗位图谱 curated 数据（45 节点）
│   ├── market_signals.json     # 市场信号数据
│   └── skill_fill_path_tags.json  # 技能补法路径分类
└── docs/
    ├── 项目概要介绍.md          # 大赛提交材料：项目概要
    ├── 项目详细方案.md          # 大赛提交材料：详细方案
    ├── PROJECT_GUIDE.md        # 项目详细讲解 + 使用指南
    └── ...                     # 其他技术规范文档
```

---

## 🎤 AI 模拟面试 — 最新特性

### 方向 Skill 驱动出题
- **6 个方向**：C++ 系统开发、前端开发、Java 后端、算法、产品经理、测试开发
- 每个方向 = SKILL.md（面试官人设）+ categories.yml（分类权重）+ 参考知识库（知识点清单）
- LLM 基于知识库动态生成题目，不是死题库

### 画像联动出题
- 自动读取**成长项目**（ProjectRecord）→ 围绕真实项目深挖技术细节
- 自动读取**目标方向 gap 技能**（CareerGoal）→ 优先考察薄弱项
- 自动读取**发展报告结论**（Report）→ 出题深度与能力评估一致
- 简历技能自动分级："熟练掌握"出深度题，"了解"出广度题

### 历史弱项复习
- 自动查询过往面试的 `skill_gaps`
- 下次出题时至少覆盖 1-2 个历史薄弱技能

### 自定义题量与题型
- 题量可选：3 / 5 / 10 题
- 题型占比可调：技术题 / 场景题 / 行为题
- 按钮文案动态：`开始面试 · 10题 · 约30分钟`

### 公平评分
- 空答案/敷衍答案 → **强制 0 分**（后端硬约束，LLM 不能给同情分）
- 有效长度检测：少于 15 字等效长度的答案直接判空

### 反幻觉约束
- 30+ 种占位符模式检测（XX/YY/ZZ/某项目/某个公司等）
- 无简历项目名时禁止编造项目名
- 过滤后的题目不足时自动 fallback 到通用题

### 模块链路打通
- **岗位图谱** → 点击"针对 XX 模拟面试"，自动预填岗位
- **JD 诊断** → 诊断结果页一键跳转，带着 JD 原文出题
- **成长档案** → 面试结果自动写入档案，形成闭环

---

## 🎓 设计哲学（三条红线）

### 1. AI 做观察，不做预言
系统**拒绝**输出"你 3 年能到高级"、"你适合做 X 方向"这类无法验证的预测。
只展示**事实陈述**（技能覆盖 X/Y · 项目证据 N 个）和**对齐分析**（你的画像跟 graph 里哪些岗位重合度高）。

### 2. 学生填真实数据，AI 不代写
档案精修模块**只给差距诊断 + 格式范本**（例如"加一个 QPS 数字会更有说服力"），
**学生必须用自己真实的项目数据填空**——强制自我反思，防止 AI 编造的假简历。

### 3. 诚实展示"我不知道"
- 当项目推荐与学生缺口严重错配时 → 显示"当前画像和典型实战项目跨度较大，建议先补基础"，**不硬塞项目**
- 当学生数据不足生成方向对齐时 → 显示"还需要更多数据"引导去补项目，**不用模板填充**
- 缺口技能按补法路径分三类（📚 学习 / 🛠️ 实践 / 🔀 先学后做），**诚实告知哪些项目能覆盖、哪些不能**

---

## 🛠️ 开发规范

Commit 规范：**Conventional Commits** 格式 `type(scope): subject`。

- `type`：`feat` / `fix` / `refactor` / `docs` / `chore` / `test` / `perf` / `style`
- `scope`：模块名（`coach` / `backend` / `skills` / `frontend` 等）
- `subject`：祈使语气，≤ 72 字符，无句号

仓库根 [`.gitmessage`](.gitmessage) 是完整模板。激活：`git config commit.template .gitmessage`（仅本仓库）。

---

## 📚 进阶阅读

- **[📑 文档索引 docs/INDEX.md](docs/INDEX.md)** · 所有文档入口（活跃 + 归档说明）
- **[🧭 项目详细讲解 + 使用指南](docs/PROJECT_GUIDE.md)** · 设计理念、模块详解、使用流程、常见问题
- **[🤖 Coach Skill 系统架构（Progressive Disclosure）](docs/coach-skill-progressive-disclosure.md)** · 当前 coach 13 skill + PD 架构权威文档
- **[🎤 模拟面试 P0 实现指南](docs/interview-p0-implementation-guide.md)** · 方向 Skill 配置 + 题库缓存 + 方向解析
- **[🔗 成长档案数据接入](docs/interview-growth-data-integration.md)** · 成长项目/gap 技能/报告结论注入 prompt
- **[🖥️ JD 诊断独立页面](docs/jd-diagnosis-page-implementation.md)** · 独立 JD 诊断页面实现方案

历史文档见 [docs/archive/](docs/archive/)。
