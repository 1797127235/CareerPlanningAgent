# Kimi Brief · 职业阶段感知 + 对比探索页实施

> 这是交给 Kimi 执行 `docs/career-stage-explore-impl-spec.md` 的提示词。复制下方 "--- PROMPT ---" 之间的内容粘给 Kimi 即可。

---

## --- PROMPT ---

你好，请执行 `C:/Users/liu/Desktop/CareerPlanningAgent` 项目里的一份 spec，落地"职业阶段感知 + 对比探索页"功能。

### 主文档

`docs/career-stage-explore-impl-spec.md` —— 改动清单、完整代码模板、验收标准、常见坑都在里面。开工前完整读一遍。

### 项目上下文（你要知道的）

- FastAPI 后端 + React/TS/Tailwind 前端
- 现有架构：React Query + React Router v6 + Tailwind + Vite
- 后端 LLM 用 DashScope（qwen-max / qwen-plus）
- 数据层 `data/graph.json` 是 gitignored 的，改动通过 `scripts/sync_graph_to_db` 同步到 DB
- 前端 API 层统一用 `frontend/src/api/client.ts` 的 `rawFetch<T>()`，带 JWT 自动注入

### 必须遵守的项目惯例（来自用户明确反复强调）

1. **反 gamification**：不允许对比卡里出现分数、百分比、进度条、雷达图、等级标签
2. **冷色玻璃美学**：用 slate-900 / slate-200 / white 配色，不许引入纸质、暖色、杂志风
3. **阶段静默判定**：不告诉用户"你处于 X 阶段"，不弹通知，纯内部状态
4. **教练语气实时感**：叙事内容已写好，不要自己改字段里的文案；如果要加任何文案，禁止出现 "截至 XXXX 年""根据数据" 等免责句式
5. **非目标严格遵守**：spec 里"不要做"的清单每条都是明令禁止，不要擅自扩大范围

### 开工前必做的 4 步校准（不做会踩坑）

**1. 验证数据就绪：**

```bash
python -c "
import json
d = json.load(open('data/graph.json', encoding='utf-8'))
has_cn = [n['node_id'] for n in d['nodes'] if n.get('contextual_narrative')]
print(f'{len(has_cn)}/45 岗位有 contextual_narrative')
print(has_cn)
"
```

期望输出 `15/45`，列表包含 java/frontend/ai-engineer/algorithm-engineer/data-analyst/python/machine-learning/full-stack/devops/cyber-security/product-manager/data-engineer/mlops/ios/android。如果不是这个数，**停下来告诉我**。

**2. 校准 GrowthEntry 模型名：**

```bash
grep -rn "class Growth" backend/db_models.py
grep -rn "growth_log\|growth_entry" backend/db_models.py
```

spec 里用的 `GrowthEntry.kind == 'interview'` 只是占位，**实际模型名和字段可能不一样**。如果现有架构用 `tags` 做面试标记而非 `kind` 字段，调整成 `tags.contains("面试")` 之类。校准完再写 `career_stage.py`。

**3. 校准 profile API 字段名：**

```bash
grep -rn "target_node_id" backend/routers/profiles.py
```

确认 `/profile` PATCH 更新目标岗位的字段名确实是 `target_node_id`。不是的话改。

**4. 找清楚 graph.py 里要加字段的地方：**

```bash
grep -n "human_ai_leverage" backend/routers/graph.py
```

有多少处 node 序列化就加多少处 `contextual_narrative`。

### 执行顺序（建议）

1. 先做后端 A.1 + A.2 + A.3（career_stage 服务 + /me/stage + graph 透字段）—— 用 curl 验证
2. 再做前端 B.1 + B.2 + B.3（类型 + API + hook）—— 只改接口层
3. 然后 B.4 + B.5 + B.6 + B.7（ExplorePage + 3 组件）—— 主功能
4. 最后 B.8 + B.9 + B.10（HomePage CTA + 两个入口链接）—— 编织

每做完一步跑一次验收命令/手动测，别攒到最后再测。

### 遇到模糊的地方

- spec 里明确的就照写
- spec 里说"校准"的就先 grep 再决定
- spec 里没讲清楚的样式细节，参照现有 `/graph` `/role/:id` 页面的视觉风格
- 遇到设计/架构上的重大偏离，**停下来问我**，不要自己决定

### 不要做

- 不要自己改 `data/graph.json` 或新增任何字段
- 不要自己改叙事内容（6 字段的文案已固化）
- 不要引入任何新依赖（zustand / framer-motion / recharts 之类）
- 不要改 `/profile` `/report` `/graph` `/growth-log` 的主体流程（只加入口）
- 不要改后端 pipeline.py / 任何 skill / LLM 调用
- 不要改 git 配置，不要 push，做完留在本地让我 review

### 完成标准

- spec 里"验收标准"的 10+ 条全部通过
- `git status` 显示改动文件符合 spec 末尾"交付物"清单
- 没有新增的 lint / type 错误（跑 `cd frontend && npm run typecheck` 无新错）
- `python -m scripts.sync_graph_to_db` 能照跑

做完把改动清单贴给我，我 review 后再说下一步。

## --- END PROMPT ---

---

## 使用说明

1. 打开 Kimi（或其它 coding agent）
2. 把上面 `--- PROMPT ---` 和 `--- END PROMPT ---` 之间的完整内容复制粘贴进去
3. Kimi 会读 `docs/career-stage-explore-impl-spec.md` 自主执行
4. 完成后 Kimi 会贴改动清单，你 review 后决定是否提交

## 为什么这么写

- **不重复 spec 内容**：Kimi 自己会读主文档，提示词只讲"怎么执行"而不是"执行什么"
- **把 memory 里的 5 条原则前置**：反 gamification / 冷色玻璃 / 静默 / 实时感 / 非目标——都是项目里血淋淋的教训沉淀
- **4 步开工校准是关键**：spec 里有些模型/字段名是占位符，Kimi 如果跳过校准会写出跑不通的代码
- **明确禁止 push**：防止 Kimi 自作主张提交（你习惯本地确认完整再提交 github）
