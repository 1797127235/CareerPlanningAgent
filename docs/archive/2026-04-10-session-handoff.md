# Session Handoff — 2026-04-10

## 本次会话完成的工作

### 1. Markdown 渲染修复
- 问题：Coach 回复显示原始 markdown 语法；react-markdown v10 移除了 default export 导致白屏
- 方案：改用 `marked` 库 + `.prose-ai` CSS 样式
- 文件：`frontend/src/components/ChatPanel.tsx`、`frontend/src/index.css`

### 2. 成长档案页面重构（GrowthLogPage）
- 清理了约 337 行死代码：旧版 PursuitModal、AddPursuitForm、PursuitsTab 及相关 import
- Overview Tab：SVG 进度环 + 日期分组时间线 + composeSentence() 状态句
- Projects Tab：ProjectsSection 组件，"+" 卡片 opacity 控制（无闪烁）
- Pursuits Tab：PursuitsSection 组件，PipelineIndicator 进度点线
- PursuitDetailModal：StatusSelector pill 按钮、JD 诊断结果展示、AI 复盘 CTA

### 3. 死代码清理 & 代码审查
- 删除：`backend/routers/mock.py`、`backend/routers/voice.py`、`backend/services/mock_service.py`
- 删除：`data/standard_jobs_embeddings.json`、相关前端组件（practice、growth 组件库）
- 清理前端路由：`/applications` → `/growth-log?tab=pursuits`

### 4. 语义意图路由（Semantic Router）
- `agent/intent_router.py`：添加文件级缓存（`_CACHE_PATH`），避免每次重启调用嵌入 API
- 路由文件：`agent/route_cache.json`（首次运行后生成）
- 关键约束：每条路由 utterances ≤ 10（DashScope 批量限制）
- 新增 `search_jd` 路由，移除对 `_SEARCH_JD_PATTERN` 正则的依赖

### 5. JD 搜索优化（search_real_jd）
- 数据源解耦：`agent/tools/career_sites.yaml`，含 15 家大厂官方校招域名
- Tavily `include_domains` 限定只搜官方校招页
- 公司级搜索：识别公司别名 → 限定到该公司单一 campus_domain
- 去重：URL base + content fingerprint
- 内容过滤：`_looks_like_jd()` 要求同时含职责和要求关键词；`_JD_NOISE_KW` 过滤 FAQ 页

### 6. JD 诊断与实战追踪联动
- `agent/tools/jd_tools.py`：
  - ContextVar 注入：`_injected_profile`、`_injected_user_id`（工具内部取，不用 LLM 传参）
  - `diagnose_jd(jd_text: str)` 单参数，消除 LLM 传参失败问题
  - `_auto_link_diagnosis_to_application()`：提取公司名 → 匹配 JobApplication FK
- ChatPanel：ActionCard 新增"加入实战追踪"按钮（jd_diagnosis 类型卡片）
- chat.py：emit card 时携带 company + position；fallback 机制（无 COACH_RESULT_ID 时找最新 CoachResult）

### 7. Agent 上下文感知
- `agent/state.py`：新增 `growth_context: dict | None` 字段
- `backend/routers/chat.py`：`_hydrate_state()` 注入 top 5 projects + active pursuits
- `agent/supervisor.py`：`build_context_summary()` 输出 growth_context 段落

### 8. 扫描版 PDF OCR 支持
- `backend/routers/profiles.py`：`_extract_pdf_text()` 双层降级
  1. pdfplumber 提取文本（文字版 PDF）
  2. pymupdf 转 PNG → base64 → DashScope qwen-vl-plus 视觉 OCR（扫描版）
- 使用 `get_env_str()` 从 backend.llm 获取正确 API key（与 os.getenv 不同）
- 测试通过：用户扫描版简历提取到 1480 字符

---

## 当前待验证 / 待完成

| 项目 | 状态 | 说明 |
|------|------|------|
| PDF 上传完整流程 | 待测试 | 画像页上传 → OCR → 画像填充 |
| JD 诊断卡片显示 | 待测试 | 重启后验证"加入实战追踪"按钮出现 |
| 实战追踪自动关联 | 待测试 | 诊断已追踪公司 JD → FK 更新 |
| PursuitDetailModal JD 结果 | 待测试 | 追踪详情页显示诊断匹配分 + gap badges |

---

## 架构关键决策记录

### ContextVar 注入模式
LangGraph 工具不能直接访问请求上下文。解决方案：在 supervisor `_make_agent_node()` 的 try 块中通过 ContextVar 注入，工具内部读取，不通过 LLM 参数传递。

### Agent vs REST 边界
- 专页功能（成长档案、求职追踪）走 REST API
- 对话驱动的分析（JD 诊断、项目建议）走 Agent 编排
- 跨模块数据（profile、growth_context）通过 CareerState 在 Agent 间共享

### JD 数据可信度
- 只从官方校招域名搜索（career_sites.yaml 配置）
- 内容双重验证：URL 过滤 + 正文关键词验证
- 不使用聚合站（boss直聘搜索页、51job搜索页等）

---

## 关键文件路径速查

```
agent/
  intent_router.py          # 语义路由 + 文件缓存
  route_cache.json          # 自动生成的嵌入缓存
  supervisor.py             # ContextVar 注入 + growth_context 构建
  tools/
    jd_tools.py             # diagnose_jd（单参数）+ 自动关联
    search_tools.py         # search_real_jd + career_sites.yaml 加载
    career_sites.yaml       # 15家大厂官方校招域名配置

backend/
  routers/
    profiles.py             # PDF OCR（pdfplumber + qwen-vl-plus）
    chat.py                 # growth_context 注入 + CoachResult card emit

frontend/src/
  components/
    ChatPanel.tsx           # marked 渲染 + ActionCard 追踪按钮
    growth-log/
      ProjectsSection.tsx
      PursuitsSection.tsx
      PursuitDetailModal.tsx
  pages/
    GrowthLogPage.tsx       # 清理后的主页面（overview + projects + pursuits）
```

---

## 下一步建议优先级

1. **P0 验证**：重启系统，跑完整 E2E：上传简历 → 画像填充 → JD 诊断 → 加入追踪 → 追踪详情显示诊断结果
2. **P1 体验**：实战追踪 AI 复盘功能（用户主动触发，3档颗粒度：快速/标准/深度）
3. **P2 增强**：Career coach 主动推送（milestone 触发）——见 docs/plan-module-integration.md
4. **P2 增强**：图谱节点技能缺口从静态改为 JD 聚合动态计算
