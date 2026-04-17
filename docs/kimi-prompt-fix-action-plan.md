# Kimi 执行：修复行动计划忽视简历项目的问题

## 问题描述

用户有 Reactor 网络库和 tcmalloc 内存池两个项目（简历解析出来的），明确展示了 C++、网络编程、多线程、内存管理能力。但报告的行动计划却说"你的成长档案中没有显示最近的实践记录"、"目前还没有具体的实践记录来支持这些技能"——把用户当零基础对待。

## 根因分析

### 根因 1：`still_claimed_only` 只看成长档案，不看简历项目

**文件**: `backend/services/report/summarize.py`，约第 608-657 行

`all_practiced` 集合只从 `ProjectRecord.skills_used`（成长档案里手动创建的项目记录）收集技能。
如果用户只上传了简历但没有在成长档案里创建项目记录，那所有技能都被标记为 `still_claimed_only`。

但简历里的项目描述（`profile_json.projects`）明确包含这些技能的实践证据。

### 根因 2：规则化 fallback 的项目匹配过于死板

**文件**: `backend/services/report/action_plan.py`，约第 59-92 行

即使关键词匹配成功（`covered_in_project = True`），生成的文本仍然是消极的："缺少系统性的知识梳理"、"缺少可量化的性能数据"。对于已有深入项目的用户，这些说法不准确。

---

## 修复方案

### 修复 1：`still_claimed_only` 增加简历项目证据检查

**文件**: `backend/services/report/summarize.py`

找到 `# ── all-time practiced (for still_claimed_only) ──` 注释（约第 608 行）。

在现有的 `all_practiced` 集合构建之后（约第 619 行，`except` 块之后），增加从简历项目中提取证据的逻辑：

```python
    # ── all-time practiced (for still_claimed_only) ──
    all_practiced: set[str] = set()
    try:
        all_projs = db.query(ProjectRecord).filter(
            ProjectRecord.user_id == user_id
        ).all()
        for p in all_projs:
            for s in (p.skills_used or []):
                if isinstance(s, str) and s.strip():
                    all_practiced.add(s.strip())
    except Exception as e:
        logger.warning("_build_skill_deltas all_practiced failed: %s", e)

    # ── 新增：从简历项目描述中提取已实践技能 ──
    try:
        profile_data = json.loads(profile.profile_json or "{}")
        resume_proj_text = " ".join(
            str(p.get("description", "") if isinstance(p, dict) else p)
            for p in (profile_data.get("projects", []) or [])
        ).lower()

        if resume_proj_text.strip():
            from backend.services.report.shared import _PROJECT_SKILL_HINTS
            # 用 _PROJECT_SKILL_HINTS 做关键词匹配
            for skill_name, hints in _PROJECT_SKILL_HINTS.items():
                if any(h in resume_proj_text for h in hints):
                    all_practiced.add(skill_name)
            # 同时检查用户声明的技能名是否直接出现在项目描述中
            for s in (profile_data.get("skills", []) or []):
                name = s.get("name", "") if isinstance(s, dict) else str(s)
                if name and len(name) >= 2 and name.lower() in resume_proj_text:
                    all_practiced.add(name.strip())
    except Exception as e:
        logger.warning("_build_skill_deltas resume_project_evidence failed: %s", e)
```

**效果**：用户简历项目里提到 "Reactor"、"epoll"、"多线程"、"内存池" 等关键词时，对应的技能（网络编程、多线程、内存管理、系统编程等）不再被标记为 `still_claimed_only`。

### 修复 2：规则化 fallback 的"已覆盖"文案改为正面引导

**文件**: `backend/services/report/action_plan.py`

找到 `covered_in_project` 为 True 时的文本生成（约第 66-73 行）。

把现有的消极文案：
```python
        if covered_in_project:
            if s["fill_path"] == "learn":
                text = f"已有项目实践涉及 {name}，但描述中缺少系统性的知识梳理和可验证的技术文档，这在面试中容易被追问。"
            elif s["fill_path"] == "practice":
                text = f"已有项目涉及 {name} 方向，但缺少可量化的性能数据、测试覆盖说明或深度技术文档，难以在面试中体现工程深度。"
            else:
                text = f"已有项目涉及 {name} 方向，但缺少可量化的性能数据、测试覆盖说明或深度技术文档，这在面试中容易被追问。"
            tag = "具体盲区"
```

改为正面+深入的引导：
```python
        if covered_in_project:
            if s["fill_path"] == "learn":
                text = f"你的项目经历已经涉及 {name}，有实践基础。下一步可以深入原理层面，把实战中踩过的坑和设计取舍整理成文档，面试时能讲出"为什么这样做"比"做了什么"更有说服力。"
            elif s["fill_path"] == "practice":
                text = f"你的项目经历已经涉及 {name}，有实践基础。如果能补充性能数据（QPS、延迟、内存占用等量化指标），简历和面试的说服力会更强。"
            else:
                text = f"你的项目经历已经涉及 {name}，有实践基础。下一步建议深入这个方向——补充量化数据或技术文档，把"用过"升级为"深入理解"。"
            tag = "深入方向"
```

---

## 验证方法

修改完后，用一个有简历项目（如 Reactor 网络库 + tcmalloc）但没有成长档案记录的用户测试：

1. 调 `GET /report/` 查看最新报告的 action_plan
2. 检查 observation 文本：
   - ❌ 不应出现"没有实践记录"、"未见具体应用场景"
   - ✅ 应出现"你的项目经历已经涉及 XX"、"有实践基础"
3. 检查 `summary_json.skill_deltas.still_claimed_only`：
   - ❌ 不应包含用户简历项目里明确涉及的技能（如 C++、网络编程、多线程）
   - ✅ 可以包含用户确实没有项目证据的技能（如 MySQL、数据结构）

## 文件改动清单

| 文件 | 改动 |
|------|------|
| `backend/services/report/summarize.py` | `_build_skill_deltas` 函数，在 `all_practiced` 后增加简历项目证据检查 |
| `backend/services/report/action_plan.py` | `_build_action_plan` 函数，改 `covered_in_project=True` 时的文案 |

## 不要做

- 不改 LLM prompt（`action-plan/SKILL.md`）—— prompt 本身写得很好，问题在数据
- 不改数据库
- 不改前端
- 不改其他 worker（narrative/diagnosis/career-alignment）
