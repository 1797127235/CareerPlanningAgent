# Plan H — 多目标岗位支持（单画像 + 多求职方向）

## 背景与问题

系统迁移为单画像后，用户只能拥有一个 `graph_position`（一个目标节点）。
但实际求职中，用户往往同时盯着多个方向（如「后端工程师」+「技术负责人」），
需要在同一个画像下管理多个目标岗位，并让下游模块（JD诊断、机会追踪、面试）感知到这些目标。

---

## 当前数据结构

```python
# db_models.py — Profile.graph_position（JSON 字段，单值）
{
  "target_node_id": "node_xxx",
  "target_label": "C++后端工程师",
  "target_zone": "transition"
}
```

---

## 方案

### 1. 新增 `CareerGoal` 表

```python
class CareerGoal(Base):
    __tablename__ = "career_goals"

    id         = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    node_id    = Column(String, nullable=False)
    node_label = Column(String, nullable=False)
    zone       = Column(String)          # safe / thrive / transition / danger
    is_primary = Column(Boolean, default=False)
    added_at   = Column(DateTime, default=datetime.utcnow)

    profile    = relationship("Profile", back_populates="career_goals")
```

Profile 保留 `graph_position` 字段仅作主目标快照（向后兼容现有读取逻辑），
权威来源切换为 `career_goals` 表。

---

### 2. 后端 API 变更

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/graph/career-goals` | 返回当前用户所有目标列表 |
| POST | `/graph/career-goals` | 添加目标节点（body: node_id, node_label, zone） |
| DELETE | `/graph/career-goals/{node_id}` | 移除某目标 |
| PUT | `/graph/career-goals/{node_id}/primary` | 设为主目标（同步写 graph_position 快照） |

原 `POST /graph/set-career-goal` 改写为调用上方 POST + PUT primary。

---

### 3. 前端变更

#### 图谱页（GraphPage）
- 节点从「单选高亮」→「多选勾选」
- 已选目标用蓝色环标记，主目标用实心蓝点区分
- 底部 panel 从「当前目标」→「已选目标列表」，支持删除、设为主目标

#### 首页画像卡（HomePage）
- `graph_position` 行改为：主目标 label + `等 N 个方向`（N > 1 时）
- 点击跳转图谱

#### 画像页（ProfilePage）
- 新增「求职方向」section，展示所有 CareerGoal
- 可在此删除某个目标或设为主目标

---

### 4. 机会管理关联（P1，可延后）

- `Application` 新增可选字段 `career_goal_id`
- JD 诊断时从已有目标中选「对比哪个方向」
- 不强制绑定，留空时按主目标处理

---

## 迁移策略

1. 存量用户：将现有 `graph_position` 自动写入 `career_goals` 表（is_primary=True）
2. 若 `graph_position` 为空则不插入，用户首次在图谱选节点时触发创建

---

## 优先级

| 优先级 | 范围 |
|--------|------|
| P0 | `career_goals` 表 + 后端 CRUD + 图谱多选 UI |
| P1 | 首页/画像页展示更新 |
| P2 | 机会管理 career_goal_id 关联 |
