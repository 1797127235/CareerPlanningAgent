# Privacy Boundary for Report Skills

## Rule

`coach_memo` (stored in `Profile.coach_memo`) is **strictly prohibited** from entering any report-generation skill prompt.

## Why

- `coach_memo` is a cross-session memo owned by the coach agent.
- It may contain sensitive, personal, or informal content.
- It belongs to the coach-facing surface only.

## Enforcement

1. `backend/services/report/summarize.py` does **not** read `profile.coach_memo`.
2. No `backend/skills/*/SKILL.md` contains a `{coach_memo*}` placeholder.
3. Unit test `tests/services/report/test_summary_privacy.py` verifies the serialized summary JSON does not leak coach_memo content.
