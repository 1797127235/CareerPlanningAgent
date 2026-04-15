# 职途智析 · AI 大学生职业规划智能体

> 基于大模型的个性化职业发展助手 —— 从简历解析到岗位对齐、从技能诊断到成长追踪，全链路帮中国 CS/IT 学生把"学了什么"转化为"能去哪里"。

---

## ✨ 核心特性

| 模块 | 能做什么 |
|------|---------|
| 🎯 **能力画像** | 上传简历自动解析 → 提炼技能/项目/经历 → SJT 软技能评估 → 在职业图谱上定位你的坐标 |
| 🗺️ **岗位图谱** | 45 个真实 IT 岗位节点 + 可视化探索 + 每个岗位含核心技能、典型实战项目、AI 影响、差异化建议 |
| 🔍 **JD 诊断** | 粘贴任意真实 JD → 四维评分（基础/技能/素养/潜力）+ 技能缺口分析 + 可落地成长建议 |
| 📈 **成长档案** | 项目追踪（记录你做过什么）+ 求职追踪（记录投递进度）+ 档案精修（学生自补空洞项目描述） |
| 📊 **AI 发展报告** | 综合评价 · 技能覆盖 · 方向对齐（LLM 分析）· 补法路径地图 · 成长计划 · AI 影响参照 |
| 💬 **AI 教练** | 右侧常驻对话面板 · 结合你当前画像/档案实时给建议 · 支持 JD 诊断、目标对齐、面试准备 |

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

**手动启动（两个终端）**：

```bash
# 终端 1：后端（端口 8000）
python -m uvicorn backend.app:app --reload

# 终端 2：前端（端口 5173）
cd frontend
npm install
npm run dev
```

浏览器打开 [http://localhost:5173](http://localhost:5173) 开始使用。

---

## 🧰 技术栈

### 后端
- **FastAPI** · 异步 API 框架
- **SQLAlchemy** + **SQLite** · ORM + 轻量数据库
- **LangGraph** · 多 Agent 编排框架
- **阿里云百炼**（qwen 系列）· 大模型推理
- **text-embedding-v3** · 语义向量计算
- **Qdrant** · 向量数据库（可选，默认嵌入式）

### 前端
- **React 19** + **TypeScript** · UI 框架
- **Vite** · 构建工具
- **TanStack Query** · 服务端状态管理
- **Tailwind CSS 4** · 样式系统（glassmorphism 设计）
- **Framer Motion** · 动效
- **Recharts** + **@xyflow/react** · 图表 + 图谱可视化
- **Lucide Icons** · SVG 图标库

### AI Agent 架构
- **Supervisor Pattern** · 中央调度器（`agent/supervisor.py`）根据意图路由到专门 Agent
- **6 个专家 Agent**：`navigator`（图谱探索）/ `growth`（成长追踪）/ `profile`（画像诊断）/ `coach`（教练对话）/ `jd`（JD 诊断）/ `search`（网络搜索）
- **Tool 层**：每个 Agent 绑定领域工具集；`coach_agent` 额外装载 pull-based context tools（`get_user_profile` / `get_career_goal` / `get_market_signal` / `get_memory_recall`）按需查询用户状态，避免 SystemMessage 全量 push
- **Skill 系统（coach 专用）** · 基于 Anthropic Skill 规范（`agent/skills/coach-*/SKILL.md`），采用 **Progressive Disclosure 模式**：catalog（13 skill 的 name + description）注入 SystemMessage（~830 tokens），LLM 判断场景后调 `load_skill(name)` tool 按需加载完整规则 —— 相比全量 push 节省 ≥ 60% token，扩到 20 skill 也只吃 ~800 tokens base cost
- **13 个 coach skill** 覆盖大学生职业规划对话场景：`greeting` / `confirmation` / `concern-direct` / `emotional-support` / `comparison-detox` / `direction-scaffold` / `progress-report` / `interview-prep` / `resume-review` / `market-signal` / `request-deliver` / `project-planning` / `decision-socratic`

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
│   │   ├── growth_log.py       # 成长档案
│   │   ├── applications.py     # 求职追踪
│   │   ├── chat.py             # AI 教练对话
│   │   └── graph.py            # 岗位图谱 API
│   └── services/               # 业务逻辑层
│       ├── report_service.py   # 报告生成核心
│       ├── jd_service.py       # JD 诊断核心
│       ├── profile_service.py  # 画像定位 + 评分
│       └── dashboard_service.py
├── agent/                      # LangGraph 多 Agent
│   ├── supervisor.py           # 中央调度器 + agent-aware context builder
│   ├── intent_router.py        # 语义意图识别
│   ├── agents/                 # 6 个专家 Agent 实现
│   ├── tools/                  # Agent 工具集（含 coach_context_tools 等）
│   └── skills/                 # Anthropic Skill 规范的 coach skill 池
│       ├── loader.py           #   · Progressive Disclosure loader（catalog + load_full）
│       └── coach-<scenario>/   #   · 每个场景独立目录 + SKILL.md（当前 13 个）
├── frontend/                   # React 前端
│   └── src/
│       ├── pages/              # 路由级页面
│       ├── components/         # 可复用组件
│       ├── api/                # HTTP 客户端
│       └── hooks/              # React hooks
├── data/
│   ├── graph.json              # 岗位图谱 curated 数据（45 节点）
│   ├── market_signals.json     # 市场信号数据
│   └── skill_fill_path_tags.json  # 技能补法路径分类
└── docs/
    ├── PROJECT_GUIDE.md        # 项目详细讲解 + 使用指南
    ├── career-alignment-spec.md
    └── ...                     # 其他技术规范文档
```

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
- **[🔧 Backend 瘦身 Phase 1](docs/backend-slimdown-phase1-profile-service.md)** · profile_service 拆分任务（进行中）

历史文档见 [docs/archive/](docs/archive/)。

---
