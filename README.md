# 智能职业规划 Agent 系统

基于岗位图谱与 LLM 的智能职业规划系统：从原始岗位数据构建职业图谱（岗位方向、技能、晋升/换岗关系、社区划分），提供 Web 端图谱浏览、路径规划与差距分析，并支持命令行 Agent 查询。

---

## 功能概览

- **职业图谱**：岗位节点、晋升/换岗边、社区划分，支持搜索与筛选
- **路径规划**：基于图谱的岗位路径推荐
- **差距分析**：岗位技能与能力差距展示
- **岗位图谱流水线**：从 CSV 岗位数据到 `graph.json` 的全自动构建（LLM 抽取 + 规则校验 + 社区发现）
- **命令行 Agent**：`main.py` 支持按岗位/城市等条件查询推荐

---

## 技术栈

| 模块     | 技术 |
|----------|------|
| 前端     | React 19 + TypeScript + Vite + Tailwind + React Flow + Recharts |
| 后端     | FastAPI + Python 3.9+ |
| 流水线   | Python（NetworkX 社区发现、OpenAI 兼容 API 如 DashScope） |
| 向量检索 | Qdrant / ChromaDB（可选） |
| LLM      | 阿里云百炼 DashScope（qwen 系列），兼容 OpenAI API |

---

## 环境要求

- **Python 3.9+**
- **Node.js 18+**（用于前端）
- **阿里云百炼 API Key**（[获取地址](https://dashscope.aliyun.com/)），用于流水线 step2/step7 与 Agent

---

## 快速开始

### 1. 克隆仓库

```bash
git clone <你的 Gitee 仓库地址>
cd CareerPlanningAgent
```

### 2. 环境变量

复制环境变量模板并填入 API Key：

```bash
copy .env.example .env
# 编辑 .env，至少填写：
# DASHSCOPE_API_KEY=sk-你的密钥
```

### 3. 一键启动（推荐）

双击或在项目根目录执行：

```bash
start.bat
```

按提示选择：

- **1**：启动 Web 服务（前端 + 后端），浏览器访问 http://localhost:5173
- **2**：仅启动后端 API，访问 http://localhost:8000/docs
- **3**：测试命令行 Agent
- **4**：运行岗位图谱流水线（全量数据需较长时间，支持断点续传）

首次运行会自动创建 `.venv`、安装 Python 依赖；若选 1 且未安装前端依赖，会提示安装 Node 依赖。

### 4. 手动启动（可选）

```bash
# 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动后端
python backend/api_integrated.py

# 另开终端：启动前端
cd frontend && npm install && npm run dev
```

前端默认：http://localhost:5173  
后端默认：http://localhost:8000

---

## 项目结构

```
CareerPlanningAgent/
├── backend/              # FastAPI 后端（API、图谱接口、报告导出等）
├── frontend/             # React 前端（Vite + TS）
├── pipeline/             # 岗位图谱构建流水线（Step 1–10）
│   ├── run.py            # 一键运行流水线
│   ├── step1_csv_to_jobs.py
│   ├── step2_extract_evidence.py   # LLM 抽取（支持 --resume 断点续传）
│   ├── step3_build_directions.py
│   ├── step4_aggregate.py
│   ├── step5_role_family.py
│   ├── step6_candidates.py
│   ├── step7_llm_edges.py
│   ├── step8_validate.py
│   ├── step9_communities.py       # 社区检测（可 --resolution 调社区数）
│   └── step10_assemble.py
├── data/                 # 原始数据（如 岗位数据.csv、skill_taxonomy.csv）
├── artifacts/            # 流水线产出与运行结果
│   ├── pipeline/         # graph.json、evidence.jsonl、profiles.json 等
│   └── graph.json        # 后端/Agent 读取的图谱入口
├── docs/                 # 文档（部署、流水线生产就绪性等）
├── main.py               # 命令行 Agent 入口
├── start.bat             # Windows 一键启动
├── requirements.txt
└── .env.example          # 环境变量模板（复制为 .env 使用）
```

---

## 岗位图谱流水线

从「岗位数据 CSV」到「图谱 JSON」的完整流程：

| 步骤 | 说明 |
|------|------|
| 1 | CSV → jobs.jsonl |
| 2 | jobs.jsonl → evidence.jsonl（LLM + 规则抽取，**支持 --resume 断点续传**） |
| 3 | evidence → directions + assignments |
| 4 | evidence → profiles.json |
| 5 | profiles → role_family.json |
| 6 | profiles + role_family → candidate_pairs.json |
| 7 | candidate_pairs → llm_edges.json（LLM 判边，有缓存可续跑） |
| 8 | llm_edges → validated_edges.json |
| 9 | validated_edges → communities.json（Louvain，可 --resolution 调社区数） |
| 10 | 全部 → graph.json |

**常用命令：**

```bash
# 完整流水线
python pipeline/run.py

# 从 step2 开始（例如已有 jobs.jsonl）
python pipeline/run.py --from 2

# step2 断点续传（中断后继续）
python pipeline/run.py --from 2 --resume

# 仅测试少量数据
python pipeline/run.py --max-jobs 500
```

产出图谱由后端从 `artifacts/pipeline/graph.json` 加载，前端「职业图谱」页即展示该数据。

---

## 环境变量说明

| 变量 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key，**必填**（流水线 step2/step7、Agent 等） |
| `DASHSCOPE_BASE_URL` | 可选，默认 DashScope 兼容 API 地址 |
| `LLM_MODEL` | 可选，默认 qwen3.5-plus |
| 其他 | 见 `.env.example` 中注释（向量库、Embedding 等） |

---

## 文档

- [流水线生产就绪性说明](docs/PIPELINE_PRODUCTION_READINESS.md)
- [部署说明](docs/DEPLOYMENT.md)（若存在）
- [流水线步骤说明](pipeline/read.md)

---

## 后续加岗位数据

1. 将新岗位数据追加或更新到 `data/岗位数据.csv`（或当前使用的 CSV）。
2. 在项目根目录重新运行流水线：  
   `python pipeline/run.py`  
   或从 step1 开始：  
   `python pipeline/run.py`  
3. 运行完成后会更新 `artifacts/pipeline/graph.json`，重启后端或刷新前端即可看到新图谱。

---

## 许可证与致谢

本项目仅供学习与组内使用。使用阿里云百炼（DashScope）请遵守其服务条款。

如有问题或建议，可在仓库提 Issue 或与维护者联系。
