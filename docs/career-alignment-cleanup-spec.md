# 职业发展路径模块 · 后端收尾清理规范

> **交付对象**：Kimi / 执行 Agent
> **版本**：v1.0 · 2026-04-14
> **前置条件**：已完成 `career-alignment-spec.md` 的前端 + 后端核心实现
> **本文档目的**：清理**旧 `promotion_path` 在报告侧的死 emission**，并更新过期 spec 附录

---

## 0. 背景

前端 `ReportPage.tsx` 已经移除对 `promotion_path` 的渲染（用 `career_alignment` 取代）。
但**后端 `report_service.py:1954`** 仍然在 `report_data` 里 emit `promotion_path` 字段——这是**数据冗余 + 语义矛盾**：

- 我们已对齐"职业发展路径由 LLM 分析（`career_alignment`）生成"
- 旧的静态 `node.promotion_path` 不再适合挂在报告 payload 里（它仍然有合法用途，但不是报告领域）

**原 spec 附录 B 里我曾写"保留旧 promotion_path 作为参考"——该判断已被用户推翻，spec 需要同步更新**。

---

## 1. 必须执行的动作

### 1.1 删除 `report_service.py` 里的 `promotion_path` emission

**文件**：`backend/services/report_service.py`
**位置**：`generate_report()` 函数内，约 1954 行附近

**当前代码**：
```python
report_data = {
    # ...
    "skill_gap": skill_gap,
    "growth_curve": growth_curve,
    "action_plan": action_plan,
    "delta": delta,
    "promotion_path": node.get("promotion_path", []),   # ← 删这一行
    "soft_skills": node.get("soft_skills", {}),
    "career_alignment": career_alignment,
    "generated_at": datetime.now(timezone.utc).isoformat(),
}
```

**改后**：
```python
report_data = {
    # ...
    "skill_gap": skill_gap,
    "growth_curve": growth_curve,
    "action_plan": action_plan,
    "delta": delta,
    "soft_skills": node.get("soft_skills", {}),
    "career_alignment": career_alignment,
    "generated_at": datetime.now(timezone.utc).isoformat(),
}
```

### 1.2 同步修正模块顶部 docstring

**文件**：`backend/services/report_service.py`
**位置**：约第 15 行

**当前**：
```python
#   data/graph.json             → promotion_path, skill_tiers, career_ceiling, etc.
```

**改为**：
```python
#   data/graph.json             → skill_tiers, career_ceiling, soft_skills, career_alignment candidates
```

> 说明：报告侧不再直接消费 `promotion_path`，但 `graph.json` 里该字段仍然保留（给 RoleDetailPage、Coverflow、graph.ts 等非报告模块使用），**不要删 graph.json**。

### 1.3 更新 `docs/career-alignment-spec.md` 的附录 B

**文件**：`docs/career-alignment-spec.md`
**位置**：附录 B · 设计决策记录

**当前**：
```markdown
- **为何保留旧 `promotion_path`**：图谱节点自带，作为"通用晋升路径参考"展示，已加 disclaimer "通用晋升路径参考 · 你的节奏取决于背景"。不与新 `career_alignment` 冲突。
```

**改为**：
```markdown
- **旧 `promotion_path` 已从报告 payload 中删除**（原 v1.0 spec 保留它的判断被推翻）。理由：和 `career_alignment` 在叙事上冗余——两个模块都在回答"职业方向如何走"，保留会让学生困惑看哪个。`graph.json` 里该字段仍保留，供 RoleDetailPage / Coverflow 等岗位详情场景使用。
```

---

## 2. 明确**不要动**的地方（反向清单）

| 位置 | 为什么不动 |
|------|----------|
| `data/graph.json` 节点里的 `promotion_path` 字段 | 这是 curated 数据，RoleDetailPage、Coverflow 等非报告模块仍在消费 |
| `frontend/src/pages/RoleDetailPage.tsx` 对 `promotion_path` 的渲染 | 岗位详情页语境正确，学生进入是为了看"该岗位的晋升路径"，这里展示合理 |
| `frontend/src/components/explorer/Coverflow.tsx` 对 `promotion_path` 的使用 | 图谱岗位卡，参考信息展示合理 |
| `frontend/src/types/graph.ts` 里的 `promotion_path` 类型 | 给上面两处用，类型必须保留 |
| `career_alignment` 相关的所有代码（`_build_career_alignment` / `_preselect_alignment_candidates` / `_load_graph_nodes` / `CareerAlignmentSection`） | 这是正确方向，不要回滚 |

---

## 3. 验证脚本（必须全部通过）

```bash
# [1] 后端 boot
python -c "from backend.app import create_app; app=create_app(); print('BOOT OK routes=', len(app.routes))"

# [2] 确认 report_service 无 promotion_path emission
grep -n "promotion_path" backend/services/report_service.py
# 预期输出：只剩 1 行（模块 docstring 已改为其他内容），不应再有 "promotion_path": node.get(...) 这行

# [3] 确认 RoleDetailPage 仍正常使用 promotion_path
grep -n "promotion_path" frontend/src/pages/RoleDetailPage.tsx | head -3
# 预期：仍然有（不许动）

# [4] 前端 typecheck
cd frontend && npx tsc --noEmit && echo FE_OK

# [5] 实际生成一份报告，检查 JSON payload
python -c "
import json
from backend.app import create_app
# 可选：如果有测试 profile_id 的话，调用 generate_report 并打印返回的 dict 的 key 列表
print('skip interactive test — 改由 UI 访问验证')
"
```

**全部通过 + 手动在浏览器里生成一份报告，验证**：
- ✓ 报告页面显示"职业发展路径"章节（新的 LLM `career_alignment`）
- ✓ 不再有任何静态阶梯时间线 "1 → 2 → 3 → 4 → 5" 的图形
- ✓ 开发者工具 Network 里检查 `/api/report/{id}` 返回的 JSON 中**不包含 `promotion_path` 字段**

---

## 4. 完成标准（DoD）

- [ ] `report_service.py:1954` 那一行 emission 已删除
- [ ] `report_service.py:15` 顶部 docstring 已同步更新
- [ ] `docs/career-alignment-spec.md` 附录 B 已同步更新
- [ ] 5 项验证脚本全部通过
- [ ] 手动在 UI 里生成报告，确认 3 项观察点
- [ ] `git diff` 只包含上述 3 个文件（`report_service.py` + 1 处代码 + 1 处 docstring；`career-alignment-spec.md` + 附录 B）—— **不应有任何其他文件变动**

---

## 5. 风险提示

| 风险 | 规避方式 |
|------|---------|
| 误删 `graph.json` 里的 `promotion_path` | 规范里明确列入"不要动"清单；git diff 应只涉及 2 个文件 |
| 误删 RoleDetailPage 的渲染 | 同上 |
| 误把 `career_alignment` 也一起删掉 | DoD 手动验证步骤会发现 |
| LLM 调用因某些原因失败 | 该路径已有 try/except 护栏，会返回 `null`，前端已有"数据不足"降级态 |

---

## 6. 这次变更本质是什么

**一句话总结**：把一个 v1.0 spec 留下的"过度保守"决策收紧——报告的"职业方向"叙事从**双轨**（老静态 + 新 LLM）收敛为**单轨**（只有新 LLM）。

**为什么现在做**：用户在 v1.0 上线后立即指出"两个模块讲一件事，冗余"—— owner 意识要求我们**不拖到下次**，当轮闭环。

---

**Kimi 交付话术**：
```
严格按本文档执行，不扩大范围、不"顺便"改其他地方。
3 处改动 + 5 条验证 + 1 次 UI 手验。
完成后贴 git diff 和 5 项验证脚本输出。
```
