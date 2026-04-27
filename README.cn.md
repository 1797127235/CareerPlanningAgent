# CareerOS · 职途智析

**面向 CS 学生的证据驱动 AI 职业规划平台。**

> CareerOS 是一个开源 AI Agent 平台。它把简历、项目、JD、面试反馈和成长记录转化为基于证据的职业规划——不是又一个通用 AI 聊天助手。

[![License: MIT](https://img.shields.io/badge/License-MIT-brown.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-brown.svg)](https://www.python.org)
[![React 19](https://img.shields.io/badge/react-19-blue.svg)](https://react.dev)

---

## 为什么是 CareerOS

| 常见问题 | CareerOS 的做法 |
|---------|----------------|
| AI 给出泛泛的职业建议，无法验证 | 每条建议都追溯到你的简历、项目或 JD 原文 |
| 只有一次性的简历分析，缺少持续追踪 | 成长档案 + 面试反馈形成长期闭环 |
| 需要 5 个工具才能覆盖求职全流程 | 统一平台：画像 → 图谱 → 诊断 → 计划 → 面试 |
| 数据上云有隐私顾虑 | 本地优先：你的数据存在你自己的电脑上 |

---

## 核心模块

| 模块 | 说明 |
|------|------|
| **能力画像** | 简历解析 → 技能提取 → SJT 评估 → 职业定位 |
| **岗位图谱** | 45 个真实 IT 岗位 + 技能要求 + AI 影响分析 + 转岗路径 |
| **JD 诊断** | 粘贴招聘要求 → 四维评分 + 技能缺口 + 提升计划 |
| **成长档案** | 项目追踪 + 求职追踪 + 技能成长时间线 |
| **职业报告** | AI 生成综合发展报告，带证据链 |
| **AI 教练** | 基于你的画像和档案实时给出建议 |
| **模拟面试** | 6 个技术方向、AI 评分、详细反馈 |

---

## 快速开始

### 前置条件

- Python 3.10+
- Node.js 18+
- [阿里云百炼 API Key](https://dashscope.aliyun.com/)（免费额度可用）

### 1. 克隆并配置

```bash
git clone https://github.com/1797127235/CareerPlanningAgent.git
cd CareerPlanningAgent
cp .env.example .env
# 编辑 .env，填入你的 DASHSCOPE_API_KEY
```

### 2. 一键启动（推荐）

```bash
run.bat
```

### 3. 手动启动

```bash
# 终端 1：后端
python -m uvicorn backend.app:app --reload

# 终端 2：前端
cd frontend-v2
npm install
npm run dev
```

### 4. 生成演示数据

```bash
python seed_demo.py
# 用户名：demo / 密码：demo123456
```

打开 [http://localhost:5174](http://localhost:5174) 开始使用。

---

## 演示

> [截图即将上线]

**快速体验路线：**
1. 上传简历 → 自动生成能力画像
2. 探索岗位图谱 → 查看 45 个 IT 岗位
3. 粘贴 JD → 获取匹配分析和技能缺口报告
4. 查看成长档案 → 追踪你的进步

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + TypeScript + Vite 8 + Tailwind CSS |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| AI Agent | LangGraph + 百炼（Qwen 系列）|
| 向量库 | Qdrant（嵌入式模式）|
| 可视化 | Recharts + React Flow |

---

## 架构

```
frontend-v2/          React SPA（主前端）
backend/              FastAPI + Agent 编排
  routers/            API 端点
  services/           业务逻辑
  skills/             Coach Skill 系统
agent/                LangGraph 多 Agent
  supervisor.py       中央调度器
  agents/             6 个专家 Agent
  tools/              Agent 工具注册表
data/                 岗位图谱 + 市场信号
```

---

## 路线图

- [x] v0.1 — 可运行的核心模块
- [ ] v0.2 — 开源包装（当前版本）
- [ ] v0.3 — MCP Server + Career Skills
- [ ] v0.4 — 多模型支持 + Evals

---

## 设计哲学

**三条红线：**

1. **AI 做观察，不做预言** — 系统拒绝输出"你 3 年能到高级"这类无法验证的预测
2. **学生填真实数据，AI 不代写** — 只给差距诊断和格式范本，不替用户编造经历
3. **诚实展示"我不知道"** — 数据不足时不硬塞建议，引导用户补充真实信息

---

## 贡献

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 安全

详见 [SECURITY.md](SECURITY.md)。

---

## 许可证

MIT License — 详见 [LICENSE](LICENSE)。

---

## 致谢

基于 LangGraph、FastAPI、React 和开源 AI 生态构建。
