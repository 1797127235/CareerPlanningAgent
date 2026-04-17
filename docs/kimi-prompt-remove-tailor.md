# Kimi 任务：移除简历定制功能

决定不再投入这个模块，完整清理所有相关代码。逐文件操作，不要遗留死代码。

---

## 1. 删除文件（3 个）

```
frontend/src/pages/ResumeTailorPage.tsx          — 删除整个文件
backend/skills/resume-tailor/SKILL.md            — 删除整个文件（连目录一起删）
docs/kimi-prompt-tailor-redesign.md              — 删除整个文件（设计稿已废弃）
```

---

## 2. `frontend/src/App.tsx`

删除 `ResumeTailorPage` 的 import 和两条路由：

```diff
- import ResumeTailorPage from '@/pages/ResumeTailorPage'

-            <Route path="/jd/tailor" element={<ResumeTailorPage />} />
-            <Route path="/jd/tailor/:diagnosisId" element={<ResumeTailorPage />} />
```

---

## 3. `frontend/src/components/Sidebar.tsx`

删除 `Sparkles` icon import（如果只有简历定制用到它）和导航项：

```diff
  import {
    ...
-   Sparkles,
    ...
  } from 'lucide-react'

  // 在 nav items 数组中删除这一行：
- { key: 'tailor', label: '简历定制', icon: Sparkles, route: '/jd/tailor' },
```

注意：检查 `Sparkles` 是否被其他地方引用，如果没有才删 import。

---

## 4. `frontend/src/pages/HomePage.tsx`

删除简历定制的快捷入口按钮。找到包含 `/jd/tailor` 的按钮块，整个删除。

同时检查 `Sparkles` import 是否还被其他地方用到，没用到就从 import 里删掉。

具体位置：搜索 `onClick={() => navigate('/jd/tailor')}`，把那整个按钮（从 `<button` 到 `</button>`）删掉。

如果删完后只剩模拟面试一个快捷按钮，把外层的 flex 容器布局调整下，一个按钮不需要两列布局。

---

## 5. `frontend/src/pages/CoachResultPage.tsx`

删除"定制简历"的下一步建议。找到包含 `/jd/tailor` 的 next step item，整行删掉。

同时检查 `Sparkles` import 是否还被其他地方用到，没用到就从 import 里删掉。

具体位置：搜索 `navigate('/jd/tailor')`，把 `buildNextSteps()` 函数里对应的那个对象删掉。

---

## 6. `backend/routers/jd.py`

删除以下内容（保留 JD 诊断相关的代码不动）：

```diff
  # 删除 _run_tailor 函数（约 15 行）
- def _run_tailor(jd_title: str, jd_text: str, result_data: dict, profile_data: dict) -> dict:
-     """Shared logic: call resume-tailor skill and return result."""
-     ...

  # 删除基于已有诊断的 tailor 端点（约 20 行）
- @router.post("/{diagnosis_id}/tailor")
- def tailor_resume(...):
-     ...

  # 删除 TailorDirectRequest model
- class TailorDirectRequest(BaseModel):
-     jd_text: str

  # 删除直接 tailor 端点（约 30 行）
- @router.post("/tailor")
- def tailor_resume_direct(...):
-     ...
```

保留不动的：`diagnose`、`list_diagnoses`、`get_diagnosis`、`rename_diagnosis`、`generate_greeting`、`delete_diagnosis` — 这些是 JD 诊断功能，和简历定制无关。

---

## 验证清单

改完后确认：

1. `grep -r "tailor\|ResumeTailor\|resume-tailor" frontend/src/ backend/` 应该没有命中（除了不相关的注释）
2. `grep -r "Sparkles" frontend/src/` 确认没有残留的未使用 import
3. `npm run dev` 前端能正常编译
4. 访问 `/jd/tailor` 应该被重定向到首页（App.tsx 的 `*` 路由兜底）
5. 侧边栏不再显示"简历定制"
6. 首页快捷工具区域布局正常
7. CoachResultPage 下一步建议里没有"定制简历"
