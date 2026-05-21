# Backend2-Only Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the legacy `backend/` runtime from production and local development, move all live API ownership into `backend2/`, and keep the existing frontend routes working during the migration.

**Architecture:** Keep the public HTTP surface stable while migrating implementation ownership. `backend2` becomes the only FastAPI process, serving both legacy `/api/*` compatibility routes and native `/api/v2/*` routes until the frontend is fully cut over. Migrate by vertical slice, not by folder copy, so each user-visible feature remains testable after every phase.

**Tech Stack:** FastAPI, SQLAlchemy, React 19, Vite proxy, LangGraph agent stack, SQLite, Pydantic v2.

---

## Release constraint

**Do not delete the legacy `backend/` during migration.**

Migration must happen in a parallel-safe mode:
- legacy `backend/` remains available as fallback
- `backend2/` takes over feature ownership slice by slice
- full frontend and manual regression testing happens before any destructive cleanup
- deletion of old runtime/modules is the final step only after acceptance sign-off

---

## Scope and non-goals

### In scope
- Collapse runtime from two uvicorn processes to one `backend2` process.
- Re-home all routes currently mounted by `backend/app.py` into `backend2`.
- Keep frontend-v2 working during migration by preserving old route contracts where needed.
- Move graph, auth, chat, report, JD diagnosis, growth log, dashboard, interview, recommendations, guidance, coach-results, and applications into `backend2` ownership.
- Update start scripts, proxy config, docs, and smoke tests.

### Out of scope
- Rewriting feature logic just to make it “more pure v2”.
- Redesigning frontend flows during backend consolidation.
- Deleting shared ORM models on day one.
- Changing business behavior unless needed for parity.

---

## Current-state inventory

### Runtime split today
- Legacy runtime: `backend/app.py`
  - mounts `/api/auth`, `/api/profiles`, `/api/graph`, `/api/jd`, `/api/chat`, `/api/report`, `/api/interview`, `/api/dashboard`, `/api/guidance`, `/api/recommendations`, `/api/coach/results`, `/api/growth-log`, `/api/applications`
- New runtime: `backend2/app.py`
  - mounts `/api/v2/health`, `/api/v2/profiles`, `/api/v2/opportunity`
- Dev launcher: `run.ps1`
  - starts `backend.app` on `8000`
  - starts `backend2.app` on `8002`
- Frontend proxy: `frontend-v2/vite.config.ts`
  - `/api` -> `8000`
  - `/api/v2` -> `8002`

### Frontend contracts that still depend on legacy `/api`
- Graph map and goal APIs: `frontend-v2/src/api/graph.ts`
- Legacy profile APIs still used by graph/report/SJT/profile chapter pieces: `frontend-v2/src/api/profiles.ts`
- Shared raw API base: `frontend-v2/src/api/client.ts`

### Known migration constraint
- `backend2` already shares some model definitions from `backend.models`.
- That means deletion of `backend/` must be staged; code ownership can move before model modules are physically moved.

---

## Migration strategy

Use a **three-layer transition**:

1. **Runtime unification layer**
   - `backend2` becomes the only running FastAPI app.
   - It serves both `/api/*` and `/api/v2/*`.

2. **Compatibility layer**
   - Legacy route contracts stay valid while frontend code is gradually pointed at v2-native contracts.
   - This avoids a flag day.

3. **Ownership cleanup layer**
   - After parity is proven, remove legacy `backend/` routers/services and collapse shared code into neutral modules if desired.

---

## File-ownership map for migration

### Existing runtime entrypoints
- Modify: `backend2/app.py`
- Modify: `run.ps1`
- Modify: `frontend-v2/vite.config.ts`
- Modify: `README.cn.md`
- Modify: `README.md`

### Legacy route owners to be migrated
- `backend/routers/auth.py`
- `backend/routers/applications.py`
- `backend/routers/chat.py`
- `backend/routers/coach_results.py`
- `backend/routers/dashboard.py`
- `backend/routers/graph.py`
- `backend/routers/growth_log.py`
- `backend/routers/guidance.py`
- `backend/routers/interview.py`
- `backend/routers/jd.py`
- `backend/routers/profiles.py`
- `backend/routers/profiles_projects.py`
- `backend/routers/profiles_sjt.py`
- `backend/routers/recommendations.py`
- `backend/routers/report.py`

### Primary backend2 landing zones
- Create/Modify: `backend2/routers/auth.py`
- Create/Modify: `backend2/routers/applications.py`
- Create/Modify: `backend2/routers/chat.py`
- Create/Modify: `backend2/routers/coach_results.py`
- Create/Modify: `backend2/routers/dashboard.py`
- Create/Modify: `backend2/routers/graph.py`
- Create/Modify: `backend2/routers/growth_log.py`
- Create/Modify: `backend2/routers/guidance.py`
- Create/Modify: `backend2/routers/interview.py`
- Create/Modify: `backend2/routers/jd.py`
- Create/Modify: `backend2/routers/profiles_legacy.py`
- Create/Modify: `backend2/routers/profiles_projects.py`
- Create/Modify: `backend2/routers/profiles_sjt.py`
- Create/Modify: `backend2/routers/recommendations.py`
- Create/Modify: `backend2/routers/report.py`

### Shared service landing zones
- Create/Modify under `backend2/services/` for each migrated subsystem.
- Keep temporary adapters to legacy service modules only where necessary for parity.

---

## Phase plan

### Phase 0: Route matrix and parity baseline

**Purpose:** Freeze the target and prevent accidental API regressions.

**Files:**
- Create: `docs/backend2-migration/route-matrix.md`
- Create: `docs/backend2-migration/parity-checklist.md`

- [ ] Build a route matrix from `backend/app.py` and `backend2/app.py`.
- [ ] Classify each route as one of:
  - already in backend2
  - frontend-v2 critical
  - internal only
  - deprecated but still reachable
- [ ] For every frontend-v2 API module under `frontend-v2/src/api/`, map it to the route contract it expects.
- [ ] Mark which routes return wrapped payloads (`{success,data,message}`) versus raw JSON.
- [ ] Define smoke tests for each top-level feature:
  - login
  - profile upload/save/load
  - graph map load
  - set career goal
  - JD diagnosis
  - report list/load/export
  - coach/chat greeting/message
  - growth log list/detail/graph
  - interview generate/submit

**Acceptance:**
- Every public route has an owner, payload shape, auth requirement, and frontend consumer list.
- No migration task starts without a parity checkbox target.

**Rollback:**
- None needed. Documentation only.

---

### Phase 1: Make backend2 the only runnable server shell

**Purpose:** Unify runtime first, without changing feature ownership yet.

**Files:**
- Modify: `backend2/app.py`
- Modify: `run.ps1`
- Modify: `frontend-v2/vite.config.ts`
- Create: `backend2/routers/legacy_health.py` if needed

- [ ] Extend `backend2/app.py` to mount both:
  - native v2 routers under `/api/v2`
  - a temporary legacy namespace under `/api`
- [ ] Add a minimal `/api/health` route in backend2 so existing health checks still pass.
- [ ] Change `run.ps1` to start only one backend process.
- [ ] Change `frontend-v2/vite.config.ts` so both `/api` and `/api/v2` proxy to the same backend2 port.
- [ ] Keep the port stable for the frontend. Prefer reusing `8000` for backend2 after cutover to reduce moving parts.

**Acceptance:**
- Local dev uses one backend process.
- Frontend proxy config has one backend target.
- `/api/health` and `/api/v2/health` both respond from backend2.

**Rollback:**
- Revert `run.ps1` and `vite.config.ts` to two-process mode.

---

### Phase 2: Migrate auth and request infrastructure first

**Purpose:** Everything else depends on auth, CORS, error shape, DB session wiring, and common dependencies.

**Files:**
- Create/Modify: `backend2/routers/auth.py`
- Create/Modify: `backend2/core/security.py`
- Create/Modify: `backend2/core/errors.py`
- Create/Modify: `backend2/db/session.py`
- Inspect and port any auth helpers now living under legacy `backend/auth.py` and `backend/routers/auth.py`

- [ ] Port `/api/auth/*` routes into backend2 with unchanged request/response contract.
- [ ] Preserve token format so frontend localStorage and auth-change events keep working.
- [ ] Preserve 401 behavior expected by:
  - `frontend-v2/src/api/client.ts`
  - `frontend-v2/src/api/profiles-v2.ts`
- [ ] Add regression checks for login/register/me/logout flows.

**Acceptance:**
- Frontend login works with backend2 only.
- All authenticated legacy and v2 routes share the same token dependency path.

**Rollback:**
- Re-enable legacy `backend` auth if token parity breaks.

---

### Phase 3: Migrate graph as the first large business slice

**Purpose:** Graph is blocking user-visible functionality today and is isolated enough to migrate early.

**Files:**
- Create: `backend2/routers/graph.py`
- Create: `backend2/services/graph/` (or neutral shared location if chosen)
- Move/adapt from:
  - `backend/routers/graph.py`
  - `backend/services/graph/service.py`
  - `backend/services/graph/query.py`
  - `backend/services/graph/path.py`
  - `backend/services/graph/matching.py`
  - `backend/services/graph/skills.py`
- Keep data assets available:
  - `data/graph.json`
  - `data/market_signals.json` if required

- [ ] Re-home `/api/graph/*` into backend2 unchanged.
- [ ] Remove legacy file path assumptions that break if modules move.
- [ ] Normalize graph data loading so it never depends on `data-deploy/graph.json` at runtime.
- [ ] Add startup or preflight checks for required data assets.
- [ ] Verify GraphPage, ExplorePage, RoleDetailPage, and Coverflow all work unchanged.

**Acceptance:**
- `/api/graph/map`, `/api/graph/search`, `/api/graph/node/*`, `/api/graph/career-goal*` all work from backend2.
- Frontend `/graph` renders with real nodes and can set goals.

**Rollback:**
- Temporarily proxy `/api/graph` back to legacy backend if graph parity fails.

---

### Phase 4: Migrate legacy profile compatibility layer

**Purpose:** Frontend-v2 still uses both legacy `/api/profiles` and v2 `/api/v2/profiles`. Backend2 must own both before old backend can disappear.

**Files:**
- Create: `backend2/routers/profiles_legacy.py`
- Create/Modify: `backend2/routers/profiles_projects.py`
- Create/Modify: `backend2/routers/profiles_sjt.py`
- Adapt from:
  - `backend/routers/profiles.py`
  - `backend/routers/profiles_projects.py`
  - `backend/routers/profiles_sjt.py`
  - `backend/routers/_profiles_helpers.py`
- Modify frontend later, but keep compatibility first:
  - `frontend-v2/src/api/profiles.ts`

- [ ] Recreate legacy `/api/profiles` contract in backend2 for:
  - fetch profile
  - update profile
  - reset profile
  - reparse profile
  - set name
  - SJT routes
  - project CRUD
- [ ] Use backend2’s profile storage as the source of truth where possible.
- [ ] Add adapter serialization so legacy consumers like `GraphPage` and `ReportListPage` still receive the old shape.
- [ ] Keep `/api/v2/profiles/*` unchanged.

**Acceptance:**
- All current frontend-v2 profile-related pages work with backend2 only.
- No old `/api/profiles` consumer requires legacy backend anymore.

**Rollback:**
- Restore `/api/profiles` proxying to old backend only if compatibility serializer proves incomplete.

---

### Phase 5: Migrate the remaining vertical slices by dependency order

**Purpose:** Retire old backend feature ownership slice by slice.

#### 5A. Dashboard + guidance + recommendations + applications

**Files:**
- Create/Modify under `backend2/routers/` and `backend2/services/` for:
  - `dashboard.py`
  - `guidance.py`
  - `recommendations.py`
  - `applications.py`

- [ ] Port low-coupling read/write APIs first.
- [ ] Preserve payload envelopes expected by frontend.

**Acceptance:**
- Home/dashboard surfaces still load.

#### 5B. JD diagnosis + opportunity alignment cleanup

**Files:**
- Create/Modify: `backend2/routers/jd.py`
- Reconcile with existing `backend2/routers/opportunity.py`

- [ ] Decide whether JD and opportunity stay separate or merge internally.
- [ ] Keep frontend entrypoints stable.

**Acceptance:**
- JD diagnosis path works fully from backend2.

#### 5C. Report pipeline

**Files:**
- Create/Modify: `backend2/routers/report.py`
- Create/Modify: `backend2/services/report/`
- Port from legacy `backend/services/report/*`

- [ ] Migrate report list, detail, generation, and export.
- [ ] Ensure graph-dependent report sections use the migrated backend2 graph service.

**Acceptance:**
- Report list/load/export all work with backend2 only.

#### 5D. Chat / coach / interview / coach-results

**Files:**
- Create/Modify: `backend2/routers/chat.py`
- Create/Modify: `backend2/routers/interview.py`
- Create/Modify: `backend2/routers/coach_results.py`
- Create/Modify: related services under `backend2/services/chat`, `backend2/services/interview`
- Coordinate with `agent/` imports and supervisor wiring

- [ ] Preserve streaming semantics for chat if frontend relies on SSE.
- [ ] Ensure backend2 app lifespan includes any scheduler/supervisor prewarm needed by these features.

**Acceptance:**
- Coach panel, greeting, chat, interview generation, and result persistence all work.

#### 5E. Growth log

**Files:**
- Create/Modify: `backend2/routers/growth_log.py`
- Create/Modify: corresponding service modules

- [ ] Port project graph endpoints and growth record CRUD.

**Acceptance:**
- Growth log pages and project graph work unchanged.

---

### Phase 6: Frontend contract cleanup after backend2 owns everything

**Purpose:** Remove compatibility debt after the backend migration is safe.

**Files:**
- Modify: `frontend-v2/src/api/client.ts`
- Modify: `frontend-v2/src/api/profiles.ts`
- Modify: `frontend-v2/src/pages/GraphPage.tsx`
- Modify any frontend module still importing legacy profile APIs if a v2-native route now exists

- [ ] Audit every import of `@/api/profiles` and decide whether to:
  - keep compatibility forever
  - or switch to v2-native contracts
- [ ] Reduce duplicate client stacks if possible (`rawFetch` vs `v2RawFetch`).
- [ ] When the frontend is fully cut over, remove the temporary legacy compatibility routers from backend2.

**Acceptance:**
- Frontend has a coherent API story.
- Legacy compatibility routes are either intentionally retained or explicitly deleted.

**Rollback:**
- Keep compatibility routers longer. No user-facing rollback needed.

---

### Phase 7: Delete legacy backend runtime

**Purpose:** Only after parity is proven and you have finished migration testing on the new backend-only path.

**Files:**
- Remove from runtime path: `backend/app.py`
- Remove or archive legacy routers/services no longer referenced
- Update docs and scripts

- [ ] Confirm no process, script, test, or import path still depends on `backend.app:app`.
- [ ] Run a full manual regression pass with legacy backend still present but unused as the primary path.
- [ ] Get explicit migration acceptance that backend2-only runtime is stable enough to remove fallback.
- [ ] Remove two-backend launch references from docs and scripts.
- [ ] Archive or delete legacy modules only after grep proves zero live imports.

**Acceptance:**
- Repository runs with one backend process.
- No feature requires the legacy backend.

**Rollback:**
- Restore old startup script and app entrypoint from git if late regression appears.

---

## Compatibility policy

### During migration
- Keep these route families stable:
  - `/api/auth/*`
  - `/api/profiles*`
  - `/api/graph/*`
  - `/api/chat/*`
  - `/api/report/*`
  - `/api/growth-log/*`
  - `/api/jd/*`
  - `/api/interview/*`
  - `/api/dashboard/*`
  - `/api/guidance/*`
  - `/api/recommendations/*`
  - `/api/coach/results/*`
  - `/api/applications/*`
- Keep `/api/v2/*` stable.

### Serialization rule
- If frontend expects `{ success, data, message }`, backend2 compatibility routes must keep that shape.
- Do not silently swap wrapped and raw JSON contracts in the same phase.

### Auth rule
- Legacy and v2 routes must accept the same bearer token during transition.

---

## Acceptance criteria

The migration is complete only when all are true:

1. One backend process serves both `/api/*` and `/api/v2/*`.
2. Frontend-v2 works without any proxy target to legacy backend.
3. These user flows pass end-to-end:
   - register/login
   - upload resume -> save profile -> load profile
   - open graph page -> load map -> set career goal
   - run JD diagnosis
   - open report list -> open detail -> export
   - open coach panel -> greeting -> send chat message
   - open growth log -> inspect project graph
   - start interview flow
4. No runtime import of `backend.app:app` remains.
5. Old backend removal does not break docs, scripts, or tests.

---

## Risks and mitigations

### Risk 1: Contract drift between legacy `/api/profiles` and v2 `/api/v2/profiles`
- **Mitigation:** Add explicit serializer adapters in backend2, not frontend rewrites first.

### Risk 2: Graph/report/chat are tightly coupled to legacy service imports
- **Mitigation:** Migrate ownership by vertical slice, keep temporary adapter imports if necessary, then clean up later.

### Risk 3: Frontend-v2 still mixes legacy and v2 APIs in the same page set
- **Mitigation:** Preserve both route families on backend2 during the entire transition.

### Risk 4: Data asset assumptions (`data/graph.json`, market signal files, exports) break after code moves
- **Mitigation:** Add startup validation and canonical data-path helpers in backend2.

### Risk 5: Scheduler / supervisor / SSE behavior regresses when chat moves
- **Mitigation:** Migrate runtime hooks before moving chat routes, and smoke-test streaming explicitly.

### Risk 6: Big-bang deletion of `backend/` leaves no rollback path
- **Mitigation:** Do not delete `backend/` until after one stable release window with backend2-only runtime.

---

## Rollback plan

### Fast rollback (same day)
- Revert `run.ps1` and `frontend-v2/vite.config.ts` to dual-backend mode.
- Re-point `/api` traffic to legacy backend.
- Keep `/api/v2` on backend2.

### Feature rollback (per slice)
- If a migrated slice fails, route only that slice back to legacy backend temporarily through proxy or startup script split.
- Do not roll back unrelated migrated slices if their parity is green.

### Hard rollback
- Restore `backend.app:app` as the primary `/api` server.
- Leave backend2 available only for `/api/v2` until fixes land.

---

## Test-before-delete gate

Before deleting any legacy backend runtime/module, kimi must complete all of the following:

1. Start the app with backend2 as the primary runtime.
2. Keep legacy backend code in the repo and available for rollback.
3. Run manual end-to-end tests for:
   - login
   - profile upload/save/load
   - graph page load and goal set
   - JD diagnosis
   - report generation/list/detail/export
   - chat/coach
   - growth log
   - interview flow
4. Run automated tests covering migrated routes.
5. Only after those pass, schedule a separate cleanup PR that removes old backend runtime/module paths.

---

## Recommended implementation order for kimi

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5A
7. Phase 5B
8. Phase 5C
9. Phase 5D
10. Phase 5E
11. Phase 6
12. Phase 7

This order gives the fastest user-visible stabilization: auth and graph first, then legacy profile compatibility, then the heavier report/chat slices.

---

## Handoff notes for implementer

- Prefer **compatibility adapters first**, cleanup second.
- Keep every phase shippable.
- After each phase, run a human-visible smoke test from frontend-v2, not just backend unit tests.
- Do not delete the legacy module tree until imports are proven dead.
- Treat `backend.models` sharing as a temporary bridge, not a final architecture.

---

Plan complete and saved to `docs/superpowers/plans/2026-05-21-backend2-only-migration.md`.

Since you said implementation will be handed to kimi, the recommended handoff is: give kimi this file plus the current route matrix/parity checklist once Phase 0 is done.
