# Soft Skills Assessment Redesign

> Date: 2026-04-04
> Status: Approved (pending implementation)

## Summary

Redesign the soft skills assessment from "5 dimensions + static 10-question SJT + LLM score fusion" to "3 dimensions + template-based LLM-personalized 15-question SJT + level display + actionable advice". LLM role shifts from scorer to context generator.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Dimensions | 3: communication, learning, collaboration | "Innovation" hard to assess via SJT; "internship" is experience not ability |
| LLM role | Template slot filler (not scorer) | LLM excels at content generation, not evaluation |
| Question source | 15 templates with slots, LLM fills per resume | Fixed efficacy ensures reliability; personalization improves relevance |
| Question count | 15 (5 per dimension) | Sweet spot: ~5-8 min, Cronbach's alpha ~0.7 |
| Score display | 4 levels (no numeric scores shown) | Avoids precision illusion; internal 0-100 retained for job matching |
| Advice | Per-dimension LLM-generated improvement tips | Scores must guide action (PM feedback) |
| Old data | Clear and re-assess | New/old methods incompatible; project in early stage |

## 1. Data Model

### Dimensions

| key | Chinese | Description |
|-----|---------|-------------|
| `communication` | 沟通能力 | Expression clarity, listening, conflict resolution |
| `learning` | 学习能力 | Knowledge absorption speed, self-driven learning, knowledge transfer |
| `collaboration` | 协作能力 | Team coordination, resource alignment, consensus building |

### Template Structure (`data/sjt_templates.json`)

```json
{
  "version": 2,
  "dimensions": ["communication", "learning", "collaboration"],
  "templates": [
    {
      "id": "t01",
      "dimension": "communication",
      "scenario_template": "你负责向{stakeholder}汇报{project_type}项目进展，但对方对技术细节不感兴趣，只关心{business_concern}。汇报前一天你发现了一个{risk_type}风险。你会怎么做？",
      "fill_slots": ["stakeholder", "project_type", "business_concern", "risk_type"],
      "options": [
        { "id": "a", "text_template": "直接用技术语言详细说明{risk_type}的影响", "efficacy": 2 },
        { "id": "b", "text_template": "用{stakeholder}关心的{business_concern}角度重新包装风险信息，提出应对方案", "efficacy": 4 },
        { "id": "c", "text_template": "先不提风险，等解决了再汇报", "efficacy": 1 },
        { "id": "d", "text_template": "让团队其他成员去汇报，避免自己传达坏消息", "efficacy": 1 }
      ]
    }
  ]
}
```

- `scenario_template`: Contains `{slot}` placeholders filled by LLM based on resume
- `options`: 4 choices with fixed efficacy (1-4), text may also have slots
- 5 templates per dimension, 15 total

### profile_json.soft_skills (v2)

```json
{
  "soft_skills": {
    "_version": 2,
    "communication": { "score": 72, "level": "良好", "advice": "你在..." },
    "learning": { "score": 65, "level": "良好", "advice": "..." },
    "collaboration": { "score": 45, "level": "基础", "advice": "..." }
  }
}
```

- `score`: Internal 0-100, used for job matching, not displayed to user
- `level`: Displayed to user (四档)
- `advice`: LLM-generated improvement suggestion
- `null` dimension value = not yet assessed

### Unassessed initial state (after resume parse)

```json
{
  "soft_skills": {
    "_version": 2,
    "communication": null,
    "learning": null,
    "collaboration": null
  }
}
```

### Level Mapping

| Score Range | Level |
|-------------|-------|
| 0-39 | 待发展 |
| 40-59 | 基础 |
| 60-79 | 良好 |
| 80-100 | 优秀 |

## 2. Assessment Flow & Backend Architecture

### Flow

```
User clicks "开始评估"
  │
  ├─ 1. POST /profiles/sjt/generate
  │    ├─ Load profile resume data
  │    ├─ Load 15 templates from sjt_templates.json
  │    ├─ LLM call: fill slots based on resume
  │    ├─ Return 15 personalized questions (no efficacy)
  │    └─ Cache generated questions (with efficacy) in SjtSession table
  │
  ├─ 2. User answers 15 questions (pick-best / pick-worst)
  │
  ├─ 3. POST /profiles/sjt/submit
  │    ├─ Retrieve questions with efficacy from session
  │    ├─ Score: best_eff + (4 - worst_eff), normalize
  │    ├─ Per-dimension average → 0-100 → level mapping
  │    ├─ LLM call: generate per-dimension advice based on answer patterns
  │    ├─ Write to profile_json.soft_skills (v2 format)
  │    └─ Return dimensions + overall_level
  │
  └─ 4. Frontend displays results
```

### API Design

#### NEW: `POST /profiles/sjt/generate`

```
Request:  { "profile_id": 123 }
Response: {
  "session_id": "uuid",
  "questions": [
    {
      "id": "t01",
      "dimension": "communication",
      "scenario": "你负责向产品总监汇报电商推荐系统项目进展...",
      "options": [
        { "id": "a", "text": "直接用技术语言详细说明..." },
        { "id": "b", "text": "用产品总监关心的转化率角度..." },
        { "id": "c", "text": "先不提风险，等解决了再汇报" },
        { "id": "d", "text": "让团队其他成员去汇报..." }
      ]
    }
  ]
}
```

#### MODIFIED: `POST /profiles/sjt/submit`

```
Request:  {
  "profile_id": 123,
  "session_id": "uuid",
  "answers": [
    { "question_id": "t01", "best": "b", "worst": "c" },
    ...
  ]
}
Response: {
  "dimensions": [
    { "key": "communication", "level": "良好", "advice": "你在风险沟通场景中..." },
    { "key": "learning", "level": "优秀", "advice": "..." },
    { "key": "collaboration", "level": "基础", "advice": "..." }
  ],
  "overall_level": "良好"
}
```

#### DELETED: `GET /profiles/sjt/questions`

No longer needed — questions are generated per-session.

### Session Storage

New table `SjtSession`:

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (UUID) | Primary key |
| profile_id | INTEGER | FK to profiles |
| questions_json | TEXT | Full questions with efficacy |
| created_at | DATETIME | |
| expires_at | DATETIME | created_at + 1 hour |

- submit validates session exists and not expired
- submit deletes session after success
- SQLite, no Redis needed

### LLM Calls

**Call 1 — Fill templates** (in generate endpoint):
- Input: 15 templates + resume summary (skills, projects, industry)
- Output: JSON with slot fill values per template
- Constraint: Do not alter option structure or efficacy, only fill slots

**Call 2 — Generate advice** (in submit endpoint):
- Input: 3 dimension scores + per-question user choices + question content
- Output: Per-dimension 50-100 char improvement advice
- Style: Positive tone, identify behavior patterns, give actionable suggestions

## 3. Frontend Changes

### SjtCtaCard Redesign

Five phases:

1. **CTA**: "完成情境评估，了解你的软技能画像" / "15 道基于你经历的情境题，约 5-8 分钟" / Button: "开始评估" → calls generate
2. **Generating**: Loading state — "正在根据你的经历生成个性化情境题..." (3-8s)
3. **Answering**: Sequential question display, pick-best/pick-worst, progress bar `X / 15`
4. **Submitting**: Loading — "正在分析你的作答..." (2-5s)
5. **Results**: 3 dimension cards (name + level badge + advice text) + overall level + close button

### SoftSkillsCard Redesign

- 3 dimensions with level badges (no numeric scores)
- Level badge colors:
  - 待发展: `slate-400` bg / `slate-700` text
  - 基础: `blue-400` bg / `blue-800` text
  - 良好: `emerald-400` bg / `emerald-800` text
  - 优秀: `amber-400` bg / `amber-800` text
- If `soft_skills._version !== 2` or dimensions are null: show "评估系统已升级，请重新测评" with inline CTA

### API Layer (`frontend/src/api/profiles.ts`)

- Add: `generateSjt(profileId) → POST /profiles/sjt/generate`
- Modify: `submitSjt(profileId, sessionId, answers) → POST /profiles/sjt/submit`
- Delete: `fetchSjtQuestions()`

## 4. Scoring Logic & Job Matching

### SJT Scoring

```
Per-question raw = best_efficacy + (4 - worst_efficacy)
  Range: 2 (best=eff1, worst=eff4) to 7 (best=eff4, worst=eff1)

Normalized = (raw - 2) / 5 * 100  → 0-100
```

Note: Corrected from current `(raw - 1) / 6` which assumes range 1-7, but actual pick-best/pick-worst range is 2-7.

Per dimension: average of 5 question scores → map to level.

### Job Matching Adaptation

`_score_qualities()` changes:
- Old: 5 dimensions weighted by `JobNode.soft_skill_weights`
- New: 3 dimensions weighted by `JobNode.soft_skill_weights`
- New weight format: `{"communication": 0.35, "learning": 0.35, "collaboration": 0.30}`
- Fallback: If job node has old 5-dim weights, use equal `{each: 0.33}`

`score_four_dimensions()` AHP weights for qualities dimension unchanged:
- Entry: 0.15, Mid: 0.25, Senior: 0.20

### Resume Parsing Changes

`_extract_profile_with_llm()`:
- Remove soft skills inference from prompt
- Resume parsing extracts only: skills, knowledge_areas, education, experience, projects
- Initialize `soft_skills` as v2 null state (see Data Model section)

## 5. Advice Generation & Error Handling

### Advice LLM Prompt

Input:
- 3 dimension scores and levels
- Per-question: scenario summary + user's best/worst picks + corresponding efficacy
- Resume summary (industry, role)

Constraints:
- 50-100 字 per dimension
- Positive tone, identify specific behavior patterns ("你倾向于...")
- Give actionable suggestions ("可以尝试...")
- Don't repeat scenario content, summarize patterns only
- Output JSON: `{"communication": "...", "learning": "...", "collaboration": "..."}`

### Error Handling

| Scenario | Response |
|----------|----------|
| Generate: LLM call fails | 500 + "生成失败，请重试", no session created |
| Generate: invalid LLM output format | Retry once, then 500 |
| Submit: session expired/missing | 410 + "评估已过期，请重新开始" |
| Submit: incomplete answers (<15) | 400 + list missing question IDs |
| Submit: advice generation fails | Scores saved normally, advice = empty string, frontend hides advice block |

### YAGNI — Explicitly Not Doing

- No assessment history — re-assessment overwrites
- No difficulty tiers — all 15 questions equal weight
- No cross-dimension analysis — independent scoring
- No percentile ranking — insufficient sample size
- No assessment frequency limits — user can re-assess anytime

## Code Deletion Checklist

| Item | Location |
|------|----------|
| `fuse_with_llm()` | `backend/services/profile_service.py` ~L1524-1540 |
| `_DEFAULT_SSW` (5-dim weights) | `backend/services/profile_service.py` ~L123-126 |
| LLM soft skills inference in resume parse | `backend/routers/profiles.py` ~L162-199 |
| `GET /profiles/sjt/questions` endpoint | `backend/routers/profiles.py` |
| `data/sjt_questions.json` | Replace with `data/sjt_templates.json` |
| `fetchSjtQuestions()` | `frontend/src/api/profiles.ts` |
| 5-dimension display logic | `frontend/src/components/profile/SoftSkillsCard.tsx` |
| Old SJT flow (static questions) | `frontend/src/components/profile/SjtCtaCard.tsx` |
