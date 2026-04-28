# Migrate Profile Read to v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Frontend reads profile via `/api/v2/profiles/me` instead of v1 `/api/profiles`, with an adapter layer so existing UI components require zero changes in Stage 1.

**Architecture:** A temporary `v2 -> v1` adapter bridges the data-format gap. This keeps Stage 1 small and low-risk. The adapter will be removed in later stages when UI components are rewritten for native v2 format.

**Tech Stack:** React + TypeScript (frontend-v2), FastAPI (backend2 already has the endpoint)

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `frontend-v2/src/types/profile-v2.ts` | Create | Canonical v2 Profile types (moved from `api/profiles-v2.ts`) |
| `frontend-v2/src/api/profiles-v2.ts` | Modify | Import types from `types/profile-v2.ts`, re-export API functions |
| `frontend-v2/src/utils/profileAdapter.ts` | Create | `v2ToV1Profile()` adapter function |
| `frontend-v2/src/hooks/useProfileDataV2.ts` | Create | New hook calling `fetchMyProfileV2()` |
| `frontend-v2/src/hooks/useProfileData.ts` | Modify | Add deprecation comment, keep for fallback |
| `frontend-v2/src/pages/ProfilePage.tsx` | Modify | Switch to `useProfileDataV2` + adapter |
| `frontend-v2/src/api/index.ts` | Modify | Barrel-export v2 API functions |

---

## Task 1: Extract v2 types to `types/profile-v2.ts`

**Files:**
- Create: `frontend-v2/src/types/profile-v2.ts`
- Modify: `frontend-v2/src/api/profiles-v2.ts`

- [ ] **Step 1: Create `types/profile-v2.ts`**

Move the v2 type definitions out of `api/profiles-v2.ts` so they can be imported by both API and UI layers without creating a circular dependency.

```typescript
// frontend-v2/src/types/profile-v2.ts

export interface V2Skill {
  name: string
  level: 'beginner' | 'familiar' | 'intermediate' | 'advanced'
}

export interface V2Education {
  degree: string
  major: string
  school: string
  graduation_year?: number
  duration: string
}

export interface V2Internship {
  company: string
  role: string
  duration: string
  tech_stack: string[]
  highlights: string
}

export interface V2Project {
  name: string
  description: string
  tech_stack: string[]
  duration: string
  highlights: string
}

export interface V2ProfileData {
  name: string
  job_target_text: string
  domain_hint: string
  education: V2Education[]
  skills: V2Skill[]
  projects: V2Project[]
  internships: V2Internship[]
  awards: string[]
  certificates: string[]
  raw_text: string
}

export interface V2ResumeDocument {
  filename: string
  content_type: string | null
  raw_text: string
  text_format: 'plain' | 'markdown'
  extraction_method: string
  ocr_used: boolean
  file_hash: string
  warnings: string[]
}

export interface V2ParseMeta {
  llm_model: string
  evidence_sources: string[]
  json_repaired: boolean
  retry_count: number
  quality_score: number
  quality_checks: Record<string, boolean>
  warnings: string[]
}

export interface V2ParsePreviewResponse {
  profile: V2ProfileData
  document: V2ResumeDocument
  meta: V2ParseMeta
}

export interface V2SaveProfileResponse {
  profile_id: number
  parse_id: number
  message: string
}
```

- [ ] **Step 2: Update `api/profiles-v2.ts` to import from `types/profile-v2.ts`**

Remove the inline type definitions from `api/profiles-v2.ts` and import them:

```typescript
// frontend-v2/src/api/profiles-v2.ts
import type {
  V2ProfileData,
  V2ParsePreviewResponse,
  V2SaveProfileResponse,
} from '@/types/profile-v2'

// Keep the API functions unchanged, just remove the inline type defs
```

- [ ] **Step 3: Commit**

```bash
git add frontend-v2/src/types/profile-v2.ts frontend-v2/src/api/profiles-v2.ts
git commit -m "refactor(types): extract v2 profile types to shared types module

Move V2ProfileData and related types from api/profiles-v2.ts to
types/profile-v2.ts for cross-layer reuse.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Create `v2ToV1Profile` adapter

**Files:**
- Create: `frontend-v2/src/utils/profileAdapter.ts`

- [ ] **Step 1: Write the adapter**

This is the critical boundary layer. It converts v2 flat format back to v1 nested format so existing UI components (`ProfileReadonlyView`, `ManualProfileForm`, etc.) work without modification.

Key mappings:
- `v2.education[]` -> `v1.profile.education` (take first element; v1 expects single object)
- `v2.skills[]` -> `v1.profile.skills` (level mapping: advanced->expert, intermediate->proficient, familiar->familiar, beginner->beginner)
- `v2.projects[]` -> `v1.profile.projects` (extract `description` as string for v1 compatibility)
- `v2.internships[]` -> `v1.profile.internships` (direct pass-through, fields match)
- `v2.certificates[]` -> `v1.profile.certificates`
- `v2.awards[]` -> not in v1, drop
- `v2.job_target_text` -> not in v1 ProfileData, but used in preview modal already
- `graph_position`, `career_goals`, `quality` -> undefined in v2, leave empty/undefined

```typescript
// frontend-v2/src/utils/profileAdapter.ts
import type { V2ProfileData } from '@/types/profile-v2'
import type { ProfileData, Skill } from '@/types/profile'

const LEVEL_MAP: Record<string, Skill['level']> = {
  beginner: 'beginner',
  familiar: 'familiar',
  intermediate: 'proficient',
  advanced: 'expert',
}

export function v2ToV1Profile(v2: V2ProfileData): ProfileData {
  const firstEdu = v2.education[0]

  return {
    id: 0, // v2 doesn't expose id; UI doesn't use it for display
    name: v2.name,
    source: 'resume',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    profile: {
      skills: v2.skills.map((s) => ({
        name: s.name,
        level: LEVEL_MAP[s.level] ?? 'familiar',
      })),
      knowledge_areas: [],
      education: firstEdu
        ? {
            degree: firstEdu.degree,
            major: firstEdu.major,
            school: firstEdu.school,
          }
        : undefined,
      experience_years: 0, // v2 doesn't have this field yet
      projects: v2.projects.map((p) => p.description || p.name),
      internships: v2.internships.map((i) => ({
        company: i.company,
        role: i.role,
        duration: i.duration,
        tech_stack: i.tech_stack,
        highlights: i.highlights,
      })),
      certificates: v2.certificates,
      soft_skills: {},
    },
    quality: {},
    graph_position: undefined,
    career_goals: undefined,
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend-v2/src/utils/profileAdapter.ts
git commit -m "feat(adapter): add v2-to-v1 profile adapter

Bridge v2 flat profile format to v1 nested format so existing
UI components require zero changes during Stage 1 migration.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Create `useProfileDataV2` hook

**Files:**
- Create: `frontend-v2/src/hooks/useProfileDataV2.ts`

- [ ] **Step 1: Write the hook**

```typescript
// frontend-v2/src/hooks/useProfileDataV2.ts
import { useState, useCallback, useEffect } from 'react'
import { fetchMyProfileV2 } from '@/api/profiles-v2'
import { v2ToV1Profile } from '@/utils/profileAdapter'
import type { ProfileData } from '@/types/profile'

export function useProfileDataV2(enabled = true) {
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState<string | null>(null)

  const loadProfile = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const v2 = await fetchMyProfileV2()
      const adapted = v2ToV1Profile(v2)
      setProfile(adapted)
    } catch (err) {
      setError(err instanceof Error ? err.message : '画像加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (enabled) loadProfile()
  }, [enabled, loadProfile])

  return { profile, loading, error, loadProfile }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend-v2/src/hooks/useProfileDataV2.ts
git commit -m "feat(hooks): add useProfileDataV2 hook with v2-to-v1 adapter

Reads profile from v2 API and adapts to v1 format for backward
compatibility with existing UI components.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Wire up `ProfilePage.tsx`

**Files:**
- Modify: `frontend-v2/src/pages/ProfilePage.tsx`

- [ ] **Step 1: Replace `useProfileData` import with `useProfileDataV2`**

Find the import line:
```typescript
import { useProfileData } from '@/hooks/useProfileData'
```

Replace with:
```typescript
import { useProfileDataV2 } from '@/hooks/useProfileDataV2'
```

Find the hook usage:
```typescript
const { profile, loading, loadError, loadProfile, ... } = useProfileData(!isMock)
```

Replace with:
```typescript
const { profile, loading, error: loadError, loadProfile } = useProfileDataV2(!isMock)
```

> Note: `useProfileDataV2` returns `error` instead of `loadError`. Map accordingly.
> Also drop fields that `useProfileDataV2` doesn't provide: `savingEdit`, `handleSaveEdit`, `handleDelete`, `handleReparse`, `reparsing`, `actionError`. These are editing functions that Stage 1 explicitly leaves on v1 (per spec compatibility matrix).

- [ ] **Step 2: Verify ProfilePage still compiles**

```bash
cd frontend-v2 && npx tsc --noEmit
```

Expected: pass (adapter ensures v1 format output)

- [ ] **Step 3: Commit**

```bash
git add frontend-v2/src/pages/ProfilePage.tsx
git commit -m "feat(frontend): ProfilePage reads profile via v2 API

Switch ProfilePage to useProfileDataV2 hook. Profile display uses
v2 backend with adapter layer; editing functions still route to v1.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Barrel-export v2 API in `api/index.ts`

**Files:**
- Modify: `frontend-v2/src/api/index.ts`

- [ ] **Step 1: Add v2 exports**

```typescript
// Add to frontend-v2/src/api/index.ts
export {
  parsePreview,
  saveProfile,
  fetchMyProfileV2,
} from './profiles-v2'
export type {
  V2ProfileData,
  V2Education,
  V2Skill,
  V2Internship,
  V2Project,
  V2ParsePreviewResponse,
  V2SaveProfileResponse,
} from '@/types/profile-v2'
```

- [ ] **Step 2: Commit**

```bash
git add frontend-v2/src/api/index.ts
git commit -m "feat(api): barrel-export v2 profile API and types

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: End-to-end verification

- [ ] **Step 1: Start backend2**

```bash
cd backend2 && python -m uvicorn backend2.app:app --reload --port 8001
```

- [ ] **Step 2: Start frontend-v2**

```bash
cd frontend-v2 && npm run dev
```

- [ ] **Step 3: Test the flow**

1. Log in (v1 auth still works, token is shared)
2. Navigate to `/profile`
3. Verify profile data loads from v2 (`GET /api/v2/profiles/me` in Network tab)
4. Verify display is correct (name, education, skills, projects, internships)

- [ ] **Step 4: Run type check**

```bash
cd frontend-v2 && npx tsc --noEmit
```

Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git commit --allow-empty -m "test(frontend): verify profile-read v2 E2E

Profile page successfully loads and displays data from v2 backend.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Mark old hook deprecated

**Files:**
- Modify: `frontend-v2/src/hooks/useProfileData.ts`

- [ ] **Step 1: Add deprecation comment**

```typescript
/**
 * @deprecated Use `useProfileDataV2` instead. This hook calls v1 API.
 * Kept temporarily for editing/SJT functions that still route to v1.
 * Will be removed when all profile operations are migrated to v2.
 */
export function useProfileData(enabled = true) { ... }
```

- [ ] **Step 2: Commit**

```bash
git add frontend-v2/src/hooks/useProfileData.ts
git commit -m "chore(hooks): mark useProfileData as deprecated

Directs future development to useProfileDataV2.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Rollback

If anything breaks:

```bash
# Revert ProfilePage.tsx to use useProfileData
git checkout HEAD~4 -- frontend-v2/src/pages/ProfilePage.tsx
git checkout HEAD~1 -- frontend-v2/src/hooks/useProfileData.ts
# Remove new files
git rm frontend-v2/src/hooks/useProfileDataV2.ts
git rm frontend-v2/src/utils/profileAdapter.ts
git rm frontend-v2/src/types/profile-v2.ts
```

Or simply: `git reset --hard HEAD~7` to roll back all Stage 1 commits.
