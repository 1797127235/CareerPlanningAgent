# Story 1.3: 题库 question_category 字段扩展

Status: ready-for-dev

## Story

As a 系统开发者,
I want 题库 InterviewQuestion 表增加 question_category 字段，
so that 未来可以按类别（技术题/行为题/系统设计题/编程题）过滤推题，为题库扩充和个性化推荐打好数据基础。

## Acceptance Criteria

1. **数据库 migration**：`interview_questions` 表新增 `question_category` 字段（VARCHAR 32，默认值 `'technical'`，nullable=False）
2. **ORM 模型更新**：`backend/db_models.py` 中 `InterviewQuestion` 类新增对应 `Mapped` 字段
3. **现有数据迁移**：已有的 506 道题全部标记为 `question_category = 'technical'`（Alembic migration 或 script 执行）
4. **API 透传**：`GET /api/practice/questions` 响应中每题包含 `question_category` 字段
5. **前端类型同步**：`frontend/src/api/practice.ts` 的 `QuestionItem` interface 新增 `question_category` 字段（可选）

## Tasks / Subtasks

- [ ] **Task 1: 更新 ORM 模型** (AC: #2)
  - [ ] 打开 `backend/db_models.py`，找到 `InterviewQuestion` 类（line ~577）
  - [ ] 在 `question_type` 字段后新增：
    ```python
    question_category: Mapped[str] = mapped_column(
        String(32), nullable=False, default="technical", index=True
    )
    ```
  - [ ] 允许值：`"technical"` | `"behavioral"` | `"system_design"` | `"coding"`

- [ ] **Task 2: 数据库 migration** (AC: #1, #3)
  - [ ] 检查项目是否使用 Alembic：`ls backend/alembic/` 或 `ls alembic/`
  - [ ] **如有 Alembic**：生成 migration `alembic revision --autogenerate -m "add question_category to interview_questions"` 并确认 upgrade script 正确
  - [ ] **如无 Alembic（直接 create_all）**：在 `backend/db.py` 或 `init_db` 处确认 `Base.metadata.create_all()` 会自动建新列（SQLite 不支持 ALTER TABLE ADD COLUMN via create_all，需手动执行 SQL）
  - [ ] 执行迁移后验证：`SELECT question_category, COUNT(*) FROM interview_questions GROUP BY question_category;` 应返回 `technical | 506`

- [ ] **Task 3: 更新题目 API 响应** (AC: #4)
  - [ ] 打开 `backend/routers/practice.py`，找到 questions 相关 endpoint
  - [ ] 确认响应 schema 中包含 `question_category` 字段（如使用 Pydantic model，添加字段；如直接 dict，确认序列化包含）

- [ ] **Task 4: 前端类型更新** (AC: #5)
  - [ ] 打开 `frontend/src/api/practice.ts`
  - [ ] 在 `QuestionItem` interface 新增：`question_category?: string`
  - [ ] 无需在当前 UI 中使用此字段，仅保证类型正确，为后续 Sprint 过滤推题做准备

## Dev Notes

### 文件改动范围

| 文件 | 改动 |
|------|------|
| `backend/db_models.py` | `InterviewQuestion` 新增 `question_category` 字段（line ~590） |
| `backend/alembic/` 或 DB init | migration script |
| `backend/routers/practice.py` | questions endpoint 响应包含新字段 |
| `frontend/src/api/practice.ts` | `QuestionItem` 新增 `question_category?: string` |

### 注意事项

- **SQLite ALTER TABLE 限制**：SQLite 不支持 `ADD COLUMN` via ORM autogenerate（部分版本除外）。如果项目使用 SQLite 且无 Alembic，手动执行：
  ```sql
  ALTER TABLE interview_questions ADD COLUMN question_category VARCHAR(32) NOT NULL DEFAULT 'technical';
  CREATE INDEX ix_interview_questions_question_category ON interview_questions(question_category);
  ```
- **本 story 不修改题目录入流程**，只扩展字段结构，后续题库扩充由单独 story 处理
- `question_type` 字段（已有，值为 `"technical"`）与新增的 `question_category` 语义不同：`question_type` 是题目形式（技术/行为/情景），`question_category` 是题目大类别，两个字段保留

### References

- `backend/db_models.py` — `InterviewQuestion` class [line ~577-599]
- `backend/routers/practice.py` — questions endpoint
- `frontend/src/api/practice.ts` — `QuestionItem` interface

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List
