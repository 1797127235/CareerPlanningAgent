---
name: Graph rebuilt from developer-roadmap
description: 2026-04-08 graph rebuilt — 34 roadmap roles, 130 edges, old pipeline deleted
type: project
---

Graph completely rebuilt from developer-roadmap data (34 CS roles, 130 edges).

**Why:** Old graph (92 nodes from scraped JD data) had non-CS roles, Chinese node_ids, stale data. New graph uses English node_ids from developer-roadmap, curated metadata for Chinese market.

**How to apply:**
- `data/graph.json` is the single source of truth (not artifacts/pipeline/)
- `data/roadmap_skills.json` has 34 roles with skill trees (3962 skills total)
- Node IDs are English (e.g., "backend", "ai-engineer") — old Chinese IDs ("后端工程师") are gone
- GraphService loads from `data/graph.json`, SkillMatchService from `data/roadmap_skills.json`
- Old `pipeline/` directory and 18 dead scripts deleted
- Existing CareerGoal records with old Chinese node_ids will be stale — re-upload resume to re-locate
- To add roles: update `backend/scripts/import_roadmap_skills.py` PRIMARY_ROLES, then run `scripts/build_roadmap_graph.py`
- Zone/salary/AI-scores are in `scripts/build_roadmap_graph.py` ROLE_META dict
