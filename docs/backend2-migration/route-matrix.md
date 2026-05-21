# Backend2 Migration — Route Matrix

> Generated during Phase 0 of backend2-only migration.

## Runtime inventory

### Legacy backend (`backend/app.py`) — port 8000

| Prefix | Router file | Tag |
|--------|-------------|-----|
| `/api/auth` | `backend/routers/auth.py` | 认证 |
| `/api/applications` | `backend/routers/applications.py` | 求职跟踪 |
| `/api/profiles` | `backend/routers/profiles.py` | 画像 |
| `/api/profiles` | `backend/routers/profiles_projects.py` | 画像 |
| `/api/profiles` | `backend/routers/profiles_sjt.py` | 画像 |
| `/api/graph` | `backend/routers/graph.py` | 图谱 |
| `/api/jd` | `backend/routers/jd.py` | JD诊断 |
| `/api/chat` | `backend/routers/chat.py` | AI对话 |
| `/api/report` | `backend/routers/report.py` | 报告 |
| `/api/interview` | `backend/routers/interview.py` | 模拟面试 |
| `/api/dashboard` | `backend/routers/dashboard.py` | 看板 |
| `/api/guidance` | `backend/routers/guidance.py` | 引导 |
| `/api/recommendations` | `backend/routers/recommendations.py` | 推荐 |
| `/api/coach/results` | `backend/routers/coach_results.py` | 教练结果 |
| `/api/growth-log` | `backend/routers/growth_log.py` | 成长档案 |
| `/api/health` | inline in `backend/app.py` | health |

### Backend2 (`backend2/app.py`) — port 8002

| Prefix | Router file | Tag |
|--------|-------------|-----|
| `/api/v2/health` | `backend2/routers/health.py` | health |
| `/api/v2/profiles` | `backend2/routers/profiles.py` | profiles |
| `/api/v2/opportunity` | `backend2/routers/opportunity.py` | opportunities |

## Frontend API consumers (`frontend-v2/src/api/`)

| File | Uses | Payload style |
|------|------|---------------|
| `client.ts` | Base fetch, auth header, 401 redirect | wrapper `{success,data,message}` via `apiFetch` |
| `profiles.ts` | `/api/profiles/*` | wrapper |
| `profiles-v2.ts` | `/api/v2/profiles/*` | raw JSON |
| `graph.ts` | `/api/graph/*` | raw JSON |
| `chat.ts` | `/api/chat/*` | raw JSON (SSE) |
| `report.ts` | `/api/report/*` | raw JSON |
| `interview.ts` | `/api/interview/*` | raw JSON |
| `jd.ts` | `/api/jd/*` | raw JSON |
| `growthLog.ts` | `/api/growth-log/*` | raw JSON |
| `applications.ts` | `/api/applications/*` | raw JSON |
| `recommendations.ts` | `/api/recommendations/*` | raw JSON |
| `coach.ts` | `/api/coach/results/*` | raw JSON |
| `user.ts` | `/api/auth/me/stage` | raw JSON |
| `profile.ts` | `/api/profiles/*` | wrapper |

## Classification

- **Already in backend2**: `/api/v2/health`, `/api/v2/profiles`, `/api/v2/opportunity`
- **Frontend-v2 critical (must migrate)**: auth, profiles (legacy), graph, chat, report, interview, jd, growth-log, applications, recommendations, coach/results, dashboard, guidance
- **Internal only**: `/api/health` (used by dev/smoke tests)
- **Deprecated but still reachable**: none identified
