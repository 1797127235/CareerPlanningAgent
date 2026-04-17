# Kimi 执行：移除硬编码技能匹配，让 LLM 自行判断项目证据

## 背景

当前 `still_claimed_only`（"仅声明、无项目证据的技能"）的判断依赖 `_PROJECT_SKILL_HINTS` 硬编码关键词映射。
这导致覆盖不全、维护成本高、结果不准。正确的做法是：把用户的技能列表和项目描述都传给 LLM，让 LLM 自己判断哪些有证据哪些没有。

## 改动原则

1. `still_claimed_only` 只基于**成长档案**（ProjectRecord）判断，不再用关键词匹配简历项目
2. LLM prompt 里明确告诉 LLM：`still_claimed_only` 是基于成长档案判断的，**简历项目可能已涉及这些技能**，请自行对照 `profile_core.projects` 判断
3. 删除 `summarize.py` 里的 `_PROJECT_SKILL_HINTS` 匹配代码块
4. `shared.py` 的 `_PROJECT_SKILL_HINTS` 保留（`action_plan.py` 和 `pipeline.py` 的规则化 fallback 仍在用），但恢复原始内容（删除我刚加的 TCP/IP、数据结构、操作系统条目）

---

## 任务 1：清理 `summarize.py`

**文件**: `backend/services/report/summarize.py`

### 1.1 删除 `_PROJECT_SKILL_HINTS` 匹配代码块

找到注释 `# ── 新增：从简历项目描述中提取已实践技能 ──`（约第 621 行），删除整个 try/except 块（约第 621-641 行）：

```python
    # ── 新增：从简历项目描述中提取已实践技能 ──    ← 删除从这里开始
    try:
        profile_data = json.loads(profile.profile_json or "{}")
        resume_proj_text = " ".join(
            ...
        ).lower()
        if resume_proj_text.strip():
            from backend.services.report.shared import _PROJECT_SKILL_HINTS
            ...
    except Exception as e:
        logger.warning("_build_skill_deltas resume_project_evidence failed: %s", e)
                                                                          ← 到这里结束
```

### 1.2 保留 `_skill_matches` 模糊匹配

`still_claimed_only` 的计算（约第 662-680 行）保持当前的 `_skill_matches` 模糊匹配逻辑不变——这个改进是正确的（处理 "C/C++" vs "C++" 的问题）。

---

## 任务 2：恢复 `shared.py` 的 `_PROJECT_SKILL_HINTS`

**文件**: `backend/services/report/shared.py`

恢复为原始 11 个条目，删除我刚加的 3 个（TCP/IP、数据结构、操作系统）和扩展的关键词：

```python
_PROJECT_SKILL_HINTS: dict[str, list[str]] = {
    "性能优化": ["性能", "高性能", "压测", "benchmark", "qps", "延迟", "吞吐", "profile", "热点", "优化"],
    "高并发":   ["并发", "高并发", "多线程", "线程池", "epoll", "reactor", "内存池", "qps", "压测"],
    "系统编程": ["系统编程", "系统调用", "内核", "epoll", "reactor", "内存池", "多线程", "linux系统", "io_uring"],
    "网络编程": ["网络", "socket", "tcp", "epoll", "reactor", "网络库", "网络框架"],
    "内存管理": ["内存", "内存池", "tcmalloc", "jemalloc", "malloc", "分配器"],
    "GDB":      ["gdb", "调试", "core dump", "断点"],
    "CMake":    ["cmake", "makefile", "构建", "编译系统"],
    "Linux":    ["linux", "系统调用", "epoll", "内核", "posix"],
    "STL":      ["stl", "标准库", "容器", "迭代器", "模板"],
    "多线程":   ["多线程", "线程池", "并发", "锁", "mutex", "原子操作"],
    "C++":      ["c++", "cpp", "stl", "模板", "虚函数"],
}
```

---

## 任务 3：更新 narrative prompt

**文件**: `backend/skills/narrative/SKILL.md`

找到第 51 行：
```
**仅列在简历、暂无项目证据的：** {still_claimed_only}
```

改为：
```
**成长档案中暂无实践记录的技能：** {still_claimed_only}
（注意：这些技能可能在用户的简历项目中已有体现，请结合上面的 milestone 和用户背景自行判断）
```

找到第 31 行：
```
- 若技能清单全为 `still_claimed_only`（无项目证据）：在手记里诚实点出这个情况，不要假装有项目支撑
```

改为：
```
- 若技能在成长档案中无记录但简历项目里有涉及：视为有实践基础，引导用户把项目经验补充到成长档案
- 若技能既无成长档案记录也无简历项目涉及：诚实点出，不要假装有项目支撑
```

---

## 任务 4：更新 action-plan prompt

**文件**: `backend/skills/action-plan/SKILL.md`

找到第 82-84 行：
```
禁止使用"你声称了 X 但没证据"的万能句式。若技能确实是 claimed-only，必须说具体：
- 错：**"你列出了 Linux 作为核心技能但没有项目里程碑验证"**（空）
- 对：**"你在 XX 公司写了 2 年 Linux 后台，但成长档案近 90 天没有 Linux 相关条目——面试追问时容易只剩下'用过'这个层次"**（具体）
```

在这段之前加一段：
```
**重要：`still_claimed_only` 仅基于成长档案记录判断，不代表用户完全没有实践经验。**
用户的简历项目（`profile_core.projects`）可能已经涉及这些技能。在写 observation 时，
必须先看 `profile_core.projects` 里有没有相关项目——如果有，说"你的 XX 项目已涉及这个方向"，
而不是说"没有实践记录"。只有简历项目里也找不到证据时，才能说缺少实践。
```

---

## 任务 5：更新 differentiation prompt

**文件**: `backend/skills/differentiation/SKILL.md`

找到第 44-46 行：
```
## 只在简历上声明、没有项目证据的技能

{still_claimed_only_line}
```

改为：
```
## 成长档案中暂无实践记录的技能（简历项目可能已涉及，请自行判断）

{still_claimed_only_line}
```

---

## 文件改动清单

| 文件 | 改动 |
|------|------|
| `backend/services/report/summarize.py` | 删除 `_PROJECT_SKILL_HINTS` 匹配代码块（约第 621-641 行） |
| `backend/services/report/shared.py` | 恢复 `_PROJECT_SKILL_HINTS` 为原始 11 条目 |
| `backend/skills/narrative/SKILL.md` | 更新 `still_claimed_only` 的说明文案 |
| `backend/skills/action-plan/SKILL.md` | 加一段"先看简历项目再判断"的指令 |
| `backend/skills/differentiation/SKILL.md` | 更新标题文案 |

## 验收

1. `summarize.py` 中不再有 `_PROJECT_SKILL_HINTS` 的 import 或使用
2. `shared.py` 的 `_PROJECT_SKILL_HINTS` 恢复为 11 个原始条目
3. 三个 prompt 文件都明确告诉 LLM：`still_claimed_only` 只基于成长档案，简历项目可能已涉及，请自行判断
4. 后端 import 正常，无报错

## 不要做

- 不删 `shared.py` 的 `_PROJECT_SKILL_HINTS`（action_plan.py 和 pipeline.py 仍在用）
- 不改 `summarize.py` 的 `_skill_matches` 模糊匹配逻辑（这个改进保留）
- 不改前端
- 不改数据库
