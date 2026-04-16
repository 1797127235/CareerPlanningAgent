# Spec：岗位 zone 值 `thrive` → `leverage` 全局统一改名

## 问题

`data/graph.json` 里 24 个节点的 `zone` 字段是 `"thrive"`，但前端（Coverflow / ReportChapter / MatchDetailPage）和 `backend/services/graph_service.py` 的寻路打分逻辑都使用 `"leverage"`。结果：

- 岗位图谱（Coverflow）"杠杆区"过滤器按 `zone === 'leverage'` 筛，永远返回 0 条
- 安全/杠杆/过渡/危险 四个分区加起来 = 13 + 0 + 7 + 1 = 21，而总数是 45
- 24 个 `thrive` 节点在图谱页完全不可见
- 同一仓库里 `thrive` 和 `leverage` 并存，多处互相不兼容

数据实际分布：`Counter({'thrive': 24, 'safe': 13, 'transition': 7, 'danger': 1})`

## 目标

以 **`leverage`** 为 canonical zone 值（因为 UI 中文标签是"杠杆区"，与 `leverage` 语义对齐），把 `thrive` 从数据、后端、前端、脚本、测试里全部替换成 `leverage`。DB 通过重跑 `scripts/sync_graph_to_db` 同步。

## 非目标（不要做）

- ❌ 不要反过来把 `leverage` 改成 `thrive` —— UI 标签是"杠杆区"，`leverage` 更贴
- ❌ 不要新增第 5 个 zone（不保留 `thrive`/`成长区`）—— 用户只有 4 区
- ❌ 不要改 `human_ai_leverage` / `leverage_base` / `leverage_breakdown` 等**列名**，它们是人机杠杆度指标，跟 zone 无关
- ❌ 不要动图谱打分 / 寻路阈值 / zone_bonus 权重
- ❌ 不要迁移 `developer-roadmap/` 下的任何东西（外部参考仓库）
- ❌ 不要改数据库 schema 或 `JobScore.zone` 字段类型（仍是 String）

---

## 改动清单

### 1. 数据 `data/graph.json`（critical）

全文替换：`"zone": "thrive"` → `"zone": "leverage"`

⚠️ **只替换 `"zone":` 上下文的 `thrive`**，如果 json 其它字段恰好有 `thrive` 字样（理论上不该有，保险起见确认一下），不要误伤。

验证：
```bash
python -c "import json; d=json.load(open('data/graph.json',encoding='utf-8')); from collections import Counter; c=Counter(n.get('zone') for n in d['nodes']); print(c)"
# 期望输出：Counter({'leverage': 24, 'safe': 13, 'transition': 7, 'danger': 1})
```

### 2. 后端 `backend/services/graph_service.py`

**第 642 行**：
```python
# 改前
elif vp == "growth" and zone == "thrive":
# 改后
elif vp == "growth" and zone == "leverage":
```

**第 644 行**：
```python
# 改前
elif vp == "innovation" and zone in ("thrive", "transition"):
# 改后
elif vp == "innovation" and zone in ("leverage", "transition"):
```

其它行（803/832/833/903/927）**已经是 `leverage`，不要动**。

### 3. 后端 `backend/routers/chat.py`

**第 613 行**（仅注释）：
```python
# 改前
# Safe/thrive + medium/high barrier: positive recommendation
# 改后
# Safe/leverage + medium/high barrier: positive recommendation
```

### 4. Agent `agent/supervisor.py`

**第 183 行**：
```python
# 改前
zone_names = {"safe": "安全区", "thrive": "成长区", "transition": "转型区", "danger": "风险区"}
# 改后
zone_names = {"safe": "安全区", "leverage": "杠杆区", "transition": "过渡区", "danger": "危险区"}
```

⚠️ 注意同时把"成长区"换成"杠杆区"，"转型区"换成"过渡区"，"风险区"换成"危险区"——与 Coverflow / ReportChapter 的中文标签保持一致。

### 5. 前端 `frontend/src/pages/HomePage.tsx`

**第 22 行**：
```tsx
// 改前
thrive:     { text: '成长区', color: 'text-blue-600 bg-blue-50' },
// 改后
leverage:   { text: '杠杆区', color: 'text-blue-600 bg-blue-50' },
```

### 6. 前端 `frontend/src/pages/ProfilePage.tsx`

**第 33-34 行**：把 `thrive` 那行删掉（`leverage` 那行保留）：
```tsx
// 改前
  thrive:     'bg-blue-50 text-blue-700',
  leverage:   'bg-blue-50 text-blue-700',
// 改后（只留 leverage）
  leverage:   'bg-blue-50 text-blue-700',
```

**第 39 行**：
```tsx
// 改前
safe: '安全区', thrive: '成长区', leverage: '杠杆区', transition: '过渡区', danger: '风险区',
// 改后
safe: '安全区', leverage: '杠杆区', transition: '过渡区', danger: '危险区',
```
（顺便把"风险区"改成"危险区"以保持一致）

### 7. 前端 `frontend/src/pages/RoleDetailPage.tsx`

**第 177 行**：
```tsx
// 改前
thrive:     'bg-blue-50 text-blue-700 border-blue-200',
// 改后
leverage:   'bg-blue-50 text-blue-700 border-blue-200',
```

**第 182 行**：
```tsx
// 改前
safe: '安全区', thrive: '成长区', transition: '过渡区', danger: '风险区',
// 改后
safe: '安全区', leverage: '杠杆区', transition: '过渡区', danger: '危险区',
```

### 8. 生成脚本（让未来新增节点写入 `leverage`）

**`scripts/add_algorithm_engineer.py`**：
- 第 20 行：`"zone": "thrive"` → `"zone": "leverage"`
- 第 200 行：`print(f"zone:                 thrive")` → `print(f"zone:                 leverage")`

**`scripts/add_system_nodes.py`**：
- 第 30、92、154 行：`"zone": "thrive"` → `"zone": "leverage"`（全部 3 处）
- 第 338 行：`print(f"... zone=thrive")` → `print(f"... zone=leverage")`

**`scripts/split_cpp_node.py`**：
- 第 17 行：`n['zone'] = 'thrive'` → `n['zone'] = 'leverage'`

### 9. 测试 `test_e2e_coach_skill.py`

**第 42 行**：
```python
# 改前
"zone": "thrive",
# 改后
"zone": "leverage",
```

### 10. DB 同步（必做）

改完 `data/graph.json` 之后，**必须跑一次**：

```bash
python -m scripts.sync_graph_to_db
```

这会 upsert `job_scores.zone`，把 24 行 `thrive` 刷成 `leverage`。脚本 idempotent，可以重复跑。

---

## 验收标准

1. **图谱页加总对上**：打开 `/graph`（Coverflow），4 个 zone filter 的计数之和 = 全部（45）。"杠杆区"按钮点下去看到 24 个岗位。

2. **数据无残留**：
   ```bash
   # 整个项目（排除 developer-roadmap/）grep 'thrive' 应该返回 0 行
   grep -r "thrive" --exclude-dir=developer-roadmap --exclude-dir=node_modules --exclude-dir=.git .
   ```
   期望结果：无输出（或仅在本 spec 文档 `docs/zone-rename-thrive-to-leverage-spec.md` 中有引用）。

3. **数据库同步**：
   ```sql
   SELECT zone, COUNT(*) FROM job_scores GROUP BY zone;
   -- 期望：leverage=24, safe=13, transition=7, danger=1
   ```

4. **打分逻辑生效**：用 `value_priority=growth` 的用户画像跑推荐，`leverage` 区节点会被加分（原来 `thrive` 分支命中，但数据里已经没 `thrive` 了，所以原来其实不命中——现在改名后命中）。

5. **中文标签一致**：所有映射表里"成长区"/"转型区"/"风险区"都换成 "杠杆区"/"过渡区"/"危险区"，与 Coverflow 的 `ZONE_FILTERS` 对齐。

6. **无其它功能回归**：
   - `/report` 生成报告正常
   - `/graph` 岗位卡片和过滤正常
   - `/role/:id` 岗位详情页的 zone 标签显示"杠杆区"而非"成长区"

---

## 关键提示

- **改完数据立刻同步 DB**：别漏 `python -m scripts.sync_graph_to_db`，否则后端打分逻辑还会看到旧 DB 值。
- **不要改 `human_ai_leverage`** / `leverage_base` / `leverage_breakdown`：这些是"人机杠杆度"指标（0-100 数值），不是 zone 枚举。
- **不要碰 `developer-roadmap/` 目录**：那是外部参考仓库克隆物，与我们无关。
- **不要改 DB 列类型**：`JobScore.zone` 是 `String`，不是枚举；不需要 migration。
- **验收第 2 步非常重要**：必须 grep 确认 `thrive` 零残留，否则后续添加节点脚本仍会写入脏数据。

完成后 `git status` 预期修改的文件：
```
M data/graph.json
M backend/services/graph_service.py
M backend/routers/chat.py
M agent/supervisor.py
M frontend/src/pages/HomePage.tsx
M frontend/src/pages/ProfilePage.tsx
M frontend/src/pages/RoleDetailPage.tsx
M scripts/add_algorithm_engineer.py
M scripts/add_system_nodes.py
M scripts/split_cpp_node.py
M test_e2e_coach_skill.py
```

加上 DB（通过脚本刷新，不在 git 里）。
