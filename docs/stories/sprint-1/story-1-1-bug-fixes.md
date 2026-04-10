# Story 1.1: Sprint 1 Bug Fixes

Status: ready-for-dev

## Story

As a user of 职途智析,
I want core UI interactions and API calls to work correctly without errors,
so that I can navigate the product without hitting broken buttons, failed searches, or HTTP errors.

## Acceptance Criteria

1. **ProfilePage 编辑按钮**：点击"编辑"按钮有明确响应（toast 提示"功能开发中"或打开编辑 modal）
2. **图谱搜索中文**：在 GraphPage 搜索框输入"前端"、"后端"、"算法"等中文关键词，能返回匹配的岗位节点（>0 条结果）
3. **GrowthPage 无 profile 422**：无 profile 或 `activeId` 为 null/0 时，GrowthPage 不发出 dashboard API 请求，展示 EmptyState 而非控制台 422 报错

## Tasks / Subtasks

- [ ] **Task 1: ProfilePage 编辑按钮** (AC: #1)
  - [ ] 定位 `frontend/src/pages/ProfilePage.tsx` 中编辑按钮（约 line 276），加 `onClick` 处理器
  - [ ] 实现：显示 toast "编辑功能开发中" 或复用 ManualProfileForm 弹出编辑态
  - [ ] 验证：点击按钮有可见响应，不再静默无反应

- [ ] **Task 2: 图谱搜索中文修复** (AC: #2)
  - [ ] 阅读 `backend/services/graph_service.py:312-330` 的 `search_nodes()` 方法
  - [ ] 根因：`keyword.lower()` 对中文字符无效（中文无大小写），且 label 字段存储的中文与 `.lower()` 结果完全一致，应该是正常的。需要检查数据是否加载正确，或 `_nodes` 是否在中文 keyword 时为空
  - [ ] 添加日志或 debug：在 `search_nodes` 入口打印 `keyword`, `len(self._nodes)` 确认数据已加载
  - [ ] 如果是数据加载时机问题：确保 `GraphService` 在 API 请求前已完成初始化（检查 `backend/routers/graph.py` 的依赖注入）
  - [ ] 验证：`GET /api/graph/search?q=前端` 返回 ≥1 条结果

- [ ] **Task 3: GrowthPage 无 profile 422 修复** (AC: #3)
  - [ ] 检查 `frontend/src/hooks/useDashboard.ts:9`：`enabled: profileId !== null` — 确认 `activeId` 在无 profile 时为 `null` 而非 `0`
  - [ ] 检查 `frontend/src/hooks/useProfileData.ts`：确认 `activeId` 初始值为 `null`，profiles 为空时不设为 `0`
  - [ ] 如 `activeId` 初始值为 `0`，将 `enabled` 改为 `enabled: !!profileId`（或 `profileId != null && profileId > 0`）
  - [ ] 验证：无 profile 账号访问 GrowthPage，控制台无 422，页面显示 EmptyState

## Dev Notes

### 文件改动范围

| 文件 | 改动 |
|------|------|
| `frontend/src/pages/ProfilePage.tsx` | 编辑按钮加 onClick（约 line 276） |
| `backend/services/graph_service.py` | `search_nodes()` debug + 修复（line 312-330） |
| `backend/routers/graph.py` | 可能需要检查 GraphService 初始化时机 |
| `frontend/src/hooks/useDashboard.ts` | `enabled` 条件加强（line 9） |
| `frontend/src/hooks/useProfileData.ts` | 确认 activeId 初始值为 null |

### 注意事项

- 编辑按钮的完整编辑功能是后续 story，本 story 只需有响应（不能静默）
- 图谱搜索修复后用中英文各测试一次，确保英文搜索也没有回退
- GrowthPage 修复后验证有 profile 时仍然正常请求 dashboard API

### References

- `backend/services/graph_service.py#search_nodes` [line 312]
- `backend/routers/dashboard.py` [line 17] — `profile_id: int = Query(...)` 必填，422 来源
- `frontend/src/hooks/useDashboard.ts` [line 9] — enabled 条件
- `frontend/src/pages/ProfilePage.tsx` [line 276] — 编辑按钮（无 onClick）

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List
