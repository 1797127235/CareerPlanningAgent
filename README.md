# CareerOS · 职途智析

**Evidence-driven AI career planning for CS students.**

> CareerOS is an open-source AI agent platform that turns resumes, projects, job descriptions, interview feedback, and growth logs into an evidence-based career plan — not just another chatbot.

[English](README.md) · [中文](README.cn.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-brown.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-brown.svg)](https://www.python.org)
[![React 19](https://img.shields.io/badge/react-19-blue.svg)](https://react.dev)

---

## Why CareerOS

| Problem | CareerOS Approach |
|---------|-------------------|
| Generic career advice with no evidence | Every recommendation traces back to your resume, projects, or JD |
| Resume-based static suggestions | Continuous growth log + interview feedback loop |
| Tool fragmentation (5 apps for 5 tasks) | Unified platform: profile → graph → diagnosis → plan → interview |
| Cloud-only with privacy concerns | Local-first: your data stays on your machine |

---

## Core Modules

| Module | Description |
|--------|-------------|
| **Student Profile** | Resume parsing → skill extraction → SJT assessment → career positioning |
| **Career Graph** | 45 real IT roles with skills, AI impact analysis, and transition paths |
| **JD Fit Analyzer** | Paste any JD → 4-dimension scoring + gap analysis + upskilling plan |
| **Growth Ledger** | Project tracking + job applications + skill development timeline |
| **Career Report** | AI-generated comprehensive career plan with evidence chain |
| **Career Coach Agent** | Real-time guidance based on your profile and growth history |
| **Interview Agent** | 6 technical tracks, AI-scored with detailed feedback |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- [DashScope API Key](https://dashscope.aliyun.com/) (free tier available)

### 1. Clone & Configure

```bash
git clone https://github.com/1797127235/CareerPlanningAgent.git
cd CareerPlanningAgent
cp .env.example .env
# Edit .env and add your DASHSCOPE_API_KEY
```

### 2. One-Click Start (Recommended)

```bash
run.bat
```

### 3. Manual Start

```bash
# Terminal 1: Backend
python -m uvicorn backend.app:app --reload

# Terminal 2: Frontend
cd frontend-v2
npm install
npm run dev
```

### 4. Seed Demo Data

```bash
python seed_demo.py
# Login: demo / demo123456
```

Open [http://localhost:5174](http://localhost:5174)

---

## Demo

> [Screenshot coming soon]

**Quick walkthrough:**
1. Upload a resume → Profile auto-generated
2. Explore Career Graph → See 45 IT roles
3. Paste a JD → Get fit analysis + gap report
4. Check Growth Ledger → Track your progress

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19 + TypeScript + Vite 8 + Tailwind CSS |
| Backend | FastAPI + SQLAlchemy + SQLite |
| AI Agent | LangGraph + DashScope (Qwen series) |
| Vector DB | Qdrant (embedded mode) |
| Visualization | Recharts + React Flow |

---

## Architecture

```
frontend-v2/          React SPA (primary)
backend/              FastAPI + agent orchestration
  routers/            API endpoints
  services/           Business logic
  skills/             Coach skill system
agent/                LangGraph multi-agent
  supervisor.py       Central dispatcher
  agents/             6 specialized agents
  tools/              Agent tool registry
data/                 Career graph + market signals
```

---

## Roadmap

- [x] v0.1 — Runnable demo with core modules
- [ ] v0.2 — Open source packaging (this release)
- [ ] v0.3 — MCP Server + Career Skills
- [ ] v0.4 — Multi-model support + Evals

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and guidelines.

---

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built with LangGraph, FastAPI, React, and the open-source AI ecosystem.
