# Session Handoff — 2026-04-08 (第二轮)

## 本次完成

### 学习资源导入（P1）
- **导入脚本** `scripts/import_roadmap_content.py` → 解析 developer-roadmap 34 角色的 4355 个 MD 文件
- **输出** `data/learning_topics.json`（3786 话题，10248 资源链接）
- **后端** `services/learning_service.py` + `GET /graph/node/{id}/learning` + `/learning/summary`
- **前端** `LearningPage.tsx` 学习资源详情页，路由 `/explore/:nodeId/learning`
- Coverflow 卡片背面新增学习资源入口

### 推荐岗位 + 动态适配度（P2）
- **后端** `services/recommendation_service.py` — 独立推荐服务，仅依赖 SkillMatchService
- **路由** `routers/recommendations.py`:
  - `GET /api/recommendations` — top-N 推荐（排除当前定位和已有目标）
  - `GET /api/recommendations/fitness?target=X` — 实时适配度 + gap_delta
  - `GET /api/recommendations/gap-analysis?role_id=X` — **LLM 模块级 gap 分析**（核心新功能）
  - `POST /api/recommendations/gap-analysis/confirm` — 用户确认已掌握
- **前端** HomePage 新增"推荐方向"卡片区块

### LLM Gap Analysis（核心改进）
- **文件** `services/gap_analyzer.py`
- **原理**: 把用户完整画像（技能+项目+经历）+ 目标角色的学习路线模块列表发给 LLM，做封闭式分类
- **效果**: C++ 用户从"还需学48%"→"已掌握90%，仅需补2个模块"
- 支持用户手动勾选"我已掌握"，存储到 `profile_json.mastered_modules`
- 结果缓存（profile_hash + role_id）

### Coverflow 卡片优化
- 去掉冗余能力条（雷达图已展示同样数据）
- 新增"详情"按钮 → 弹出模态框（intro + 薪资 + 职级 + 能力值 + 技能 + 学习入口）
- 去掉 hover 浮层（3D transform 下定位不可靠）

### 雷达图修复
- 替换硬编码维度：~~职级深度~~→**技能广度**（skill_count），~~成长空间~~→**转型灵活度**（degree）
- 后端 `/graph/map` 新增 `skill_count` + `degree` 字段
- 归一化从线性改为 sqrt + floor（防止低值维度塌陷）

### 技能翻译
- `scripts/translate_skills_parallel.py` — 5 线程并行 LLM 批量翻译
- 3134/3293 英文技能名翻译为中文，写入 `roadmap_skills.json`
- gap 展示全中文

### 匹配算法改进
- gap 从 topics（大类目）改为 skills（具体技能）
- 位置 + 长度双重过滤替代硬编码正则
- 最终由 LLM gap analysis 接管 gap 展示质量

### 代码清理
- Fix `profiles.py:248` undefined `position` bug → `best.affinity`
- Delete `resource_retriever.py`（无调用方）
- Remove `infer_skills_esco()` 90 行死方法

### Gemini 前端任务
- `docs/prompt-gemini-gap-frontend.md` — Gap Analysis 前端集成 prompt
- 包含 API 接口、TypeScript 类型、设计规范、交互细节
- Gemini 负责改造 ProfilePage "匹配方向" Panel

---

## 关键文件清单

| 文件 | 作用 |
|------|------|
| `data/learning_topics.json` | 3786 话题 + 10248 资源链接 |
| `data/roadmap_skills.json` | 34 角色技能树（含 skills_zh 中文翻译） |
| `backend/services/gap_analyzer.py` | LLM 模块级 gap 分析 |
| `backend/services/learning_service.py` | 学习资源服务 |
| `backend/services/recommendation_service.py` | 推荐岗位服务 |
| `backend/routers/recommendations.py` | 推荐 + gap 分析 + 确认 API |
| `frontend/src/pages/LearningPage.tsx` | 学习资源详情页 |
| `scripts/import_roadmap_content.py` | 学习资源导入 |
| `scripts/translate_skills_parallel.py` | 技能名批量翻译 |

---

## 已知影响
1. **ProfilePage "匹配方向"卡片** — Gemini 正在改造，集成 gap-analysis API
2. **SkillMatchService 的 gap_skills** — token 匹配的 gap 仍在返回，但前端应优先展示 LLM gap analysis 结果
3. **developer-roadmap 源数据** — 已移到项目内 `developer-roadmap/` 目录

---

## 下一步（按选题要求优先级）

### P1：岗位画像补充软技能维度
- 选题要求：岗位画像包含专业技能、证书要求、创新能力、学习能力、抗压能力、沟通能力、实习能力
- 现状：graph.json 只有 must_skills / core_tasks，DB 模型有 soft_skills 字段但无数据
- 方案：数据驱动推导（从 replacement_pressure / human_ai_leverage / degree / career_level 计算）+ LLM 微调
- 存入 graph.json 的每个节点

### P2：SJT 补 2 个维度
- 选题要求：创新能力、抗压能力
- 现状：sjt_templates.json 只有 3 维（沟通/学习/协作）
- 方案：新增 10 个模板（创新×5 + 抗压×5），同结构

### P3：垂直晋升路径
- 选题要求：涵盖岗位描述、岗位晋升路径关联
- 现状：career_level 1-5 数字，无明确晋升链
- 方案：为每个角色定义 L1-L5 的具体职级名称 + 相邻职级间的晋升边

### P4：报告 PDF 导出 + 手动编辑 + 智能润色
- 选题要求：报告智能润色、完整性检查、手动编辑、一键导出
- 现状：window.print() 伪导出，无编辑功能
- 方案：后端 PDF 生成（WeasyPrint/Playwright）、前端 contentEditable 编辑、LLM 润色 endpoint
