# Backend2 Migration — Parity Checklist

> Phase 0 baseline. Each item must pass before legacy backend can be retired.

## Backend ownership status

| Route family | Owner | Migrated to backend2 |
|-------------|-------|---------------------|
| `/api/auth/*` | `backend2/routers/auth.py` | ✅ |
| `/api/profiles/*` | `backend2/routers/profiles_legacy.py` | ✅ |
| `/api/profiles/*` (projects) | `backend2/routers/profiles_projects.py` | ✅ |
| `/api/profiles/*` (SJT) | `backend2/routers/profiles_sjt.py` | ✅ |
| `/api/graph/*` | `backend2/routers/graph.py` | ✅ |
| `/api/jd/*` | `backend2/routers/jd.py` | ✅ |
| `/api/chat/*` | `backend2/routers/chat.py` | ✅ |
| `/api/report/*` | `backend2/routers/report.py` | ✅ |
| `/api/interview/*` | `backend2/routers/interview.py` | ✅ |
| `/api/dashboard/*` | `backend2/routers/dashboard.py` | ✅ |
| `/api/guidance/*` | `backend2/routers/guidance.py` | ✅ |
| `/api/recommendations/*` | `backend2/routers/recommendations.py` | ✅ |
| `/api/coach/results/*` | `backend2/routers/coach_results.py` | ✅ |
| `/api/growth-log/*` | `backend2/routers/growth_log.py` | ✅ |
| `/api/applications/*` | `backend2/routers/applications.py` | ✅ |
| `/api/v2/*` | `backend2/routers/*` (native v2) | ✅ |

## Smoke test flows

- [x] **Register / Login**
  - POST `/api/auth/register` returns `{success,data,message}` ✅
  - POST `/api/auth/login` returns token + user ✅
  - GET `/api/auth/me/stage` returns career stage ✅
  - Frontend stores token in localStorage, dispatches `auth-change` ✅

- [ ] **Profile upload / save / load**
  - POST `/api/profiles/parse-resume` parses resume
  - PUT `/api/profiles` saves profile (merge/replace)
  - GET `/api/profiles` loads current profile ✅
  - PATCH `/api/profiles/name` sets display name

- [x] **Graph page load + set career goal**
  - GET `/api/graph/map` returns nodes + edges ✅
  - GET `/api/graph/node/{id}` returns node detail
  - PUT `/api/graph/career-goal` sets goal
  - GET `/api/graph/search?q=...` returns search results

- [ ] **JD diagnosis**
  - POST `/api/jd/diagnose` returns match score + gaps
  - GET `/api/jd/history` lists past diagnoses
  - GET `/api/jd/{id}` returns single diagnosis

- [ ] **Report list / detail / export**
  - GET `/api/report/` lists reports
  - POST `/api/report/generate` creates report
  - GET `/api/report/{id}` returns detail
  - POST `/api/report/{id}/export` returns PDF

- [ ] **Coach / Chat**
  - GET `/api/chat/greeting` returns greeting + chips
  - POST `/api/chat` streams SSE with session_id, content, card
  - GET `/api/chat/sessions` lists sessions
  - GET `/api/chat/sessions/{id}/messages` returns messages

- [ ] **Growth log**
  - GET `/api/growth-log/entries` lists entries
  - GET `/api/growth-log/dashboard` returns dashboard data
  - POST `/api/growth-log/projects` creates project

- [ ] **Interview flow**
  - POST `/api/interview/start` generates questions
  - POST `/api/interview/{id}/follow-up` generates follow-up
  - POST `/api/interview/{id}/submit` evaluates answers
  - GET `/api/interview/history` lists past interviews

- [ ] **Dashboard / Guidance / Recommendations / Applications**
  - GET `/api/dashboard` returns home dashboard
  - GET `/api/guidance/*` returns guidance state
  - GET `/api/recommendations` returns recommendations
  - GET/POST `/api/applications/*` CRUD applications

## Serialization parity

| Route family | Wrapper `{success,data,message}` | Raw JSON |
|-------------|----------------------------------|----------|
| `/api/auth/*` | ✅ register, login | ✅ me/stage |
| `/api/profiles/*` | ✅ GET, PUT, PATCH, DELETE, projects | ✅ SJT endpoints |
| `/api/graph/*` | ❌ | ✅ all |
| `/api/jd/*` | ❌ | ✅ all |
| `/api/chat/*` | ❌ | ✅ all (SSE) |
| `/api/report/*` | ❌ | ✅ all |
| `/api/interview/*` | ❌ | ✅ all |
| `/api/dashboard/*` | ❌ | ✅ all |
| `/api/guidance/*` | ❌ | ✅ all |
| `/api/recommendations/*` | ❌ | ✅ all |
| `/api/coach/results/*` | ❌ | ✅ all |
| `/api/growth-log/*` | ❌ | ✅ all |
| `/api/applications/*` | ❌ | ✅ all |
| `/api/v2/*` | ❌ | ✅ all |

## Auth parity

- [x] Legacy `/api/*` and v2 `/api/v2/*` accept the same Bearer token format ✅
- [x] 401 behavior triggers frontend redirect to `/login` ✅
- [x] Token creation uses identical secret + algorithm ✅

## Runtime changes

- [x] `run.ps1` starts only one backend process (backend2 on port 8000) ✅
- [x] `frontend-v2/vite.config.ts` proxies both `/api` and `/api/v2` to port 8000 ✅
- [x] `deploy/career-agent.service` points to `backend2.app:app` ✅
- [x] `Dockerfile` points to `backend2.app:app` ✅
- [x] `README.md` / `README.cn.md` updated ✅

## Cleanup status (Phase 7)

- [x] `backend/app.py` removed from runtime path ✅
- [x] `backend/routers/` removed (all routers migrated to `backend2/routers/`) ✅
- [x] Zero live imports of `backend.routers` verified (`grep` clean) ✅
- [x] `tests/routers/test_auth.py` updated to test `backend2.app` ✅
- [x] `agent/tools/` references to `backend.routers` fixed ✅
- [x] `backend/services/graph/locator.py` reference to `backend.routers` fixed ✅
- [x] `backend.services.profile_service` → `backend.services.profile` fixed ✅

## Remaining shared code (still in `backend/`, actively used by backend2)

- `backend/models/` — ORM models (shared database schema)
- `backend/db.py` — SQLAlchemy Base + engine (used by backend2.db.session)
- `backend/services/` — Business logic services
- `backend/auth.py` — Legacy auth utilities (some services may still reference)
- `backend/config.py` — Legacy config
- `backend/utils.py` — `ok()` helper
- `backend/llm.py` — LLM client
- `backend/skills/` — Skill invocation framework
