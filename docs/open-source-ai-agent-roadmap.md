# 开源化与 AI Agent 化路线指导

最后更新：2026-04-28

## 一句话定位

把本项目从「AI 大学生职业规划系统」收束成：

> **本地优先、证据驱动、可扩展的开源 AI 职业规划 Agent 平台。**

核心差异不是自动海投，而是帮助 CS/IT 学生把简历、项目、JD、岗位图谱、面试反馈和成长记录串成一条可验证的职业发展闭环。

## 先做这些

这些任务不需要大改架构，优先级最高。做完后，项目会从「功能很多但散」变成「别人能跑、能看懂、愿意 fork」。

| 优先级 | 任务 | 目标 | 验收方式 |
|---|---|---|---|
| P0 | 修 Agent 导入错误 | `agent.llm` 能正常导入，Supervisor 能构建 | `python -c "from agent.supervisor import _get_cached_supervisor; _get_cached_supervisor(); print('ok')"` |
| P0 | 修测试旧路径 | 测试至少能完成收集并开始执行 | `python -m pytest -q tests` 不再 collection error |
| P0 | 统一启动说明 | README、`run.ps1`、Vite 端口一致 | 按 README 从零启动成功 |
| P0 | 加 `/api/health` | Docker healthcheck 和人工检查都可用 | `curl http://localhost:8000/api/health` 返回 ok |
| P0 | 明确主前端 | `frontend-v2` 是主前端，旧 `frontend` 标记 legacy | README 和部署文档不再混用 |
| P0 | 统一数据路径 | fresh clone 后能获得图谱数据 | 提供 `data-deploy -> data` 初始化脚本或让代码默认 fallback |
| P0 | 加 demo seed | 新贡献者不用上传真实简历也能体验闭环 | 一条命令生成 demo user/profile/JD/report |
| P0 | 清理开源入口 | README、`.env.example`、许可证、贡献入口清楚 | GitHub 首页 3 分钟内看懂和跑起 |

建议第一批提交顺序：

1. `fix(agent): restore supervisor startup`
2. `fix(tests): update legacy imports`
3. `docs(readme): align startup commands and ports`
4. `feat(system): add health check endpoint`
5. `chore(data): add demo data bootstrap`

## 现在暴露出的工程问题

### Agent 主链路不稳

当前 `agent/llm.py` 重新导出 `load_env`，但 `backend/llm.py` 中实际函数名是 `_load_env`。这会导致部分 Agent 构建失败。

建议修法：

- 在 `backend/llm.py` 中增加公开别名 `load_env = _load_env`，保持向后兼容。
- 或者删掉 `agent/llm.py` 对 `load_env` 的重新导出。
- 修完后补一个最小测试，防止回归。

### 测试和代码结构脱节

目前测试里还有旧导入：

- `from backend.models import Base`
- `from backend.services import coach_memory`

建议修法：

- 从 `backend.db` 重新导出或在测试中改为 `from backend.db import Base`。
- 给 `backend.services.coach_memory` 做兼容 shim，指向 `backend.services.coach.memory`。
- 如果模块已废弃，明确删除对应旧测试，不要让坏测试长期留在仓库里。

### 启动与部署说明不一致

需要统一：

- README 写的是 `start.bat`，实际存在的是 `run.bat`。
- `run.ps1` 输出前端 5173，但 `frontend-v2/vite.config.ts` 是 5174。
- Docker Compose 挂载 `frontend/dist`，但当前主前端是 `frontend-v2`。
- Docker healthcheck 请求 `/api/health`，但后端当前没有这个接口。

这些问题技术难度不高，但对开源第一印象影响很大。

## 开源项目包装

开源项目的第一目标不是「功能最多」，而是让陌生人愿意相信它、跑起来、改一处小东西并提交 PR。

### 必备文件

| 文件 | 作用 |
|---|---|
| `README.md` | 项目定位、截图/GIF、快速开始、核心能力 |
| `README.en.md` | 面向国际开发者和 Agent 生态 |
| `CONTRIBUTING.md` | 本地开发、测试、PR 规范 |
| `SECURITY.md` | API key、简历数据、LLM 隐私边界 |
| `LICENSE` | 明确开源许可，建议 MIT 或 Apache-2.0；如果未来做 SaaS，可考虑 AGPL |
| `.env.example` | 所有环境变量解释，不含真实 key |
| `docs/architecture.md` | 后端、前端、Agent、数据层的真实结构 |
| `docs/demo-guide.md` | 评委/贡献者 5 分钟演示路线 |

### GitHub 首页要展示的东西

- 一张产品主界面截图。
- 一个 60-120 秒 demo GIF 或视频链接。
- 一条最短启动路径。
- 一个 demo 账号或 demo seed。
- 清楚说明本项目不自动海投、不伪造简历、不替用户提交申请。
- 标出「适合贡献的 first issues」。

## AI 时代应补的能力

### 1. MCP Server

MCP 是 AI 应用连接外部工具和数据的开放标准。你的项目应该把职业规划能力暴露出去，而不是只藏在 Web UI 里。

第一版 MCP tools 可以很小：

| Tool | 输入 | 输出 |
|---|---|---|
| `analyze_resume` | resume text / file path | 结构化画像 |
| `diagnose_jd` | JD text + profile id | 匹配分、缺口、证据 |
| `recommend_roles` | profile id | 推荐岗位与理由 |
| `get_skill_gap` | profile id + role id | 技能差距 |
| `generate_interview_plan` | profile id + role/JD | 面试准备计划 |
| `update_growth_log` | user id + event | 成长记录 |

验收方式：

- Claude Desktop、Cursor、Codex 或其他 MCP client 能调用至少 3 个工具。
- README 有 MCP 配置样例。
- 所有工具都不返回敏感原文，默认只返回必要摘要。

参考：[MCP 官方介绍](https://modelcontextprotocol.io/docs/getting-started/intro)

### 2. Skills 包

你的 `agent/skills/coach-*` 和 `backend/skills/*` 是很有价值的资产。建议把它们整理成可复用的 Agent Skills。

第一批可开源 Skills：

- `career-coach`
- `resume-review`
- `jd-diagnosis`
- `interview-prep`
- `growth-planning`
- `career-decision-socratic`

每个 Skill 要包含：

- `SKILL.md`
- 触发场景
- 输入边界
- 禁止事项，例如不得编造项目、不得承诺录取概率
- 示例输入/输出

参考：[Anthropic Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills)

### 3. Evidence Trace

职业建议必须能追溯来源。每条重要建议都应该带证据链：

```json
{
  "claim": "你更适合从 Java 后端方向切入",
  "evidence": [
    {"type": "resume_skill", "text": "Spring Boot, MySQL"},
    {"type": "project", "text": "秒杀系统项目包含 Redis 和 MQ"},
    {"type": "role_graph", "text": "Java 后端岗位核心技能重合 68%"}
  ],
  "inference": "项目证据能覆盖岗位核心后端链路，但高并发压测证据不足"
}
```

这会让项目区别于普通 chatbot。

### 4. Evals

开源 AI 项目要有 evals。建议先做离线评测，不急着做复杂平台。

目录建议：

```text
evals/
  cases/
    resume_parse/
    jd_diagnosis/
    interview_eval/
    hallucination_guard/
  expected/
  run_evals.py
```

第一批评测点：

- 不编造用户项目。
- 空简历不得强行推荐具体岗位。
- JD 诊断必须引用 JD 或画像证据。
- 面试空答案必须给低分。
- 报告不得泄露 `coach_memo` 等隐私字段。

### 5. Human-in-the-loop

职业规划涉及用户人生选择，不应该全自动替用户决定。

建议把高风险动作全部设为需要确认：

- 修改简历内容。
- 生成投递材料。
- 写入长期记忆。
- 标记职业目标。
- 输出强结论，例如「你不适合某方向」。

LangGraph 的 interrupt / persistence 适合做暂停与恢复。参考：[LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)

### 6. Durable Execution

报告生成、JD 批处理、岗位扫描、长对话总结都属于长任务。后续应该支持失败恢复，而不是失败后重跑全部。

建议从两个流程开始：

- `generate_report`
- `mock_interview_eval`

参考：[LangGraph durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution)

### 7. 多模型 Provider

开源项目不要强绑定单一模型。建议抽象：

```text
LLM_PROVIDER=dashscope | openai | anthropic | gemini | ollama
LLM_BASE_URL=
LLM_MODEL=
EMBEDDING_PROVIDER=
EMBEDDING_MODEL=
```

第一阶段继续保留 OpenAI-compatible 客户端即可，但 README 要说明怎么切换。

## 不建议现在做的事

| 事情 | 原因 |
|---|---|
| 自动海投 | 容易碰到平台 ToS、伦理和账号风险，也会稀释你的「职业规划」定位 |
| 大规模重写前端 | 当前前端能 build，优先解决可运行、可贡献、可追踪 |
| 盲目换框架 | 你已经用了 LangGraph，先补 persistence、trace、evals |
| 继续堆页面 | 目前瓶颈是工程收束和开源包装，不是功能数量 |
| 追求全自动职业决策 | 职业规划应保留人类确认和不确定性表达 |

## 推荐路线图

### Phase 0：开源可信度修复，1-3 天

- 修 Agent 导入错误。
- 修测试收集错误。
- 统一 README、run 脚本、端口、Docker 文档。
- 加 `/api/health`。
- 添加 demo seed。
- 清楚标记 `frontend-v2` 为主前端。

完成标准：

```bash
python -m pytest -q tests
cd frontend-v2 && npm run build
python -m uvicorn backend.app:app --reload
```

至少以上命令路径清晰，失败时错误可解释。

### Phase 1：开源入口，3-7 天

- 中文/英文 README。
- `CONTRIBUTING.md`、`SECURITY.md`、`LICENSE`。
- `docs/demo-guide.md`。
- Demo GIF。
- GitHub issue labels：`good first issue`、`agent`、`frontend`、`evals`、`docs`。
- 增加 GitHub Actions：后端测试 + 前端 build。

完成标准：

- 陌生开发者 10 分钟内能跑起 demo。
- README 不依赖你本人解释。

### Phase 2：AI Agent 平台化，1-2 周

- MCP Server MVP。
- Skills 包整理。
- Evidence Trace MVP。
- 离线 evals。
- LLM provider 抽象。
- 写一份 `docs/agent-architecture.md`。

完成标准：

- 其他 AI client 能调用你的职业规划能力。
- 每条重要建议能看到证据来源。
- 至少 10 个 eval case 能稳定通过。

### Phase 3：差异化能力，2-4 周

- 成长档案和面试反馈形成长期闭环。
- 图谱推荐支持用户目标、项目证据、市场信号三方校准。
- 生成「项目补证计划」，告诉用户缺哪些真实证据，而不是替用户编简历。
- 做匿名样例数据集，方便研究和复现。

完成标准：

- 项目不只是求职工具，而是一个持续成长的职业 Agent。

## 对标项目和启发

| 项目/标准 | 可学习点 | 不照搬点 |
|---|---|---|
| [career-ops](https://github.com/santifer/career-ops) | 开源包装、多 CLI 支持、doctor、示例、免责声明、human-in-the-loop | 它偏求职操作系统，你应保留职业规划深度 |
| [ApplyPilot](https://github.com/Pickle-Pixel/ApplyPilot) | Pipeline 清晰、CLI 简单、阶段可单独运行 | 自动投递风险较高，不适合作为你的核心方向 |
| [MCP](https://modelcontextprotocol.io/docs/getting-started/intro) | 把系统能力暴露给其他 AI 应用 | 初期不要做太多工具，先做 3-6 个稳定工具 |
| [A2A](https://a2a-protocol.org/latest/) | 未来 Agent 间协作方向 | 现阶段先 MCP，A2A 可作为后续实验 |
| [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents) | handoffs、tools、guardrails、tracing、evals 的产品化思路 | 不必立刻迁移 SDK，先补你现有 LangGraph 的缺口 |
| [LangGraph durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution) | 长任务恢复、人类确认、可中断执行 | 先在报告和面试两个流程试点 |

## 项目原则

1. **证据优先**：建议必须来自简历、项目、JD、图谱或市场数据，不能凭空断言。
2. **学生真实成长优先**：AI 可以指出缺口、给模板、拆计划，但不替用户编造经历。
3. **本地优先**：简历、画像、成长记录默认存在用户本地。
4. **可解释优先**：每个推荐都能回答「为什么」。
5. **可扩展优先**：核心能力通过 API、MCP、Skills 暴露，不只服务 Web UI。
6. **人类确认优先**：涉及长期记忆、简历修改、职业目标选择时必须让用户确认。

## 第一批适合拆成 Issue 的任务

- `fix: agent.llm load_env compatibility`
- `fix: update tests for backend.db Base export`
- `fix: add coach_memory compatibility module or update tests`
- `feat: add /api/health endpoint`
- `docs: align README startup command with run.bat`
- `docs: mark frontend-v2 as primary frontend`
- `chore: add data bootstrap script from data-deploy`
- `feat: add demo seed command`
- `feat: add MCP server skeleton`
- `feat: expose diagnose_jd as MCP tool`
- `test: add hallucination guard eval cases`
- `docs: add SECURITY.md for resume/privacy handling`

## 最小成功标准

如果只能做一个小版本，目标定为：

> 陌生人 clone 仓库后，10 分钟内跑起 demo；Claude/Cursor/Codex 能通过 MCP 调用一次 JD 诊断；README 能清楚解释项目不是自动海投，而是证据驱动的职业规划 Agent。

做到这里，项目就已经具备开源项目的基本气质。
