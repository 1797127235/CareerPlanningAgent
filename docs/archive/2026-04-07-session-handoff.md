# Session Handoff — 2026-04-07

## 架构理解（重要，新会话必读）

### 单画像设计
- 一个用户永远只有一个 `Profile` 记录（不删除，只更新数据）
- 多次上传简历 → **合并**进同一个 profile（`_merge_profile_data`）
- `profile_json` / `quality_json` 存技能、经历、评分
- 单画像解决的是"多版本简历管理混乱"问题

### CareerGoal 表的双重职责
- **锚点记录**（系统自动创建）：`target_node_id == from_node_id`，记录用户在图谱中的当前位置
  - 由 `_auto_locate_on_graph()` 在上传简历后自动创建
  - 作为 escape-routes 的出发点
- **用户目标**（用户显式设置）：`target_node_id != from_node_id`，在图谱页设定
  - 一个主目标（`is_primary=True`）+ 多个候选

### graph_position 字段
- 不是独立的 DB 字段，由 `_profile_to_dict()` 从 `CareerGoal.from_node_id` 派生
- 重置画像后 career_goals 被删，graph_position 自然消失

---

## 本次已完成的改动

### ProfilePage 重构（frontend/src/pages/ProfilePage.tsx）
- 从 788 行复杂布局重写为 Bento Grid（12列）
- 身份卡 / AI诊断 / 目标岗位 / 能力维度 / 技能 / 推荐路线 / 软技能 7张卡
- 软技能等级修复：读 `softSkills.communication.level`（不是对象本身）
- AI诊断文案：基于 gap_skills + competitiveness 动态生成
- 重置入口移除（移到首页）

### 重置画像流程
- **首页**（HomePage.tsx）放置重置按钮，inline 确认，不跳转
- 首页分支条件改为 `!profileLoading && !hasProfile`（脱离 stale guidance 缓存）
- `useProfileData.handleDelete` 改为调 `loadProfile()` 而非 `setProfile(null)`

### 后端重置接口（backend/routers/profiles.py）
- `DELETE /profiles` 现在同时清除：
  - `profile_json = "{}"`
  - `quality_json = "{}"`
  - 所有 CareerGoal 记录（**按 user_id 过滤**，不用 profile_id）
  - 原因：数据库中存在多画像时代的残留数据，profile_id 过滤不完整

```python
db.query(CareerGoal).filter(
    CareerGoal.user_id == user.id
).delete(synchronize_session=False)
```

---

## 待验证问题

### 重置画像是否彻底清除（核心问题）
- **现象**：重置后画像页仍显示"当前岗位"和"目标岗位"
- **原因**：DB 中存在 user_id=6 的 career_goals 有两个不同 profile_id（4 和 16），多画像残留
- **修复**：已改为 `filter(CareerGoal.user_id == user.id)`
- **需要**：重启后端后重新测试

### 验证步骤
```
1. 重启后端（确保新代码生效）
2. 在首页点重置画像 → 确认
3. 检查画像页是否不再显示当前岗位 / 目标岗位
4. 上传新简历 → 确认自动定位恢复
```

---

## 数据库现状（2026-04-07）
career_goals 表有残留的多画像时代数据，user_id=6 有 profile_id=6 和 profile_id=16 两条记录。
可手动清理：
```sql
DELETE FROM career_goals WHERE user_id = 6;
```

---

## 文件索引

| 文件 | 改动摘要 |
|------|---------|
| `frontend/src/pages/ProfilePage.tsx` | Bento Grid 重构，软技能修复，重置入口移除 |
| `frontend/src/pages/HomePage.tsx` | 重置按钮，分支条件改为 !hasProfile |
| `frontend/src/hooks/useProfileData.ts` | handleDelete 调 loadProfile() |
| `backend/routers/profiles.py` | reset_profile 按 user_id 删 career_goals |
| `backend/services/graph_service.py` | escape-routes 区域多样性（上次会话） |
