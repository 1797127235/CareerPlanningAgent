# Story 1.2: 多维度评分模型（后端 + 前端展示）

Status: ready-for-dev

## Story

As a 用户做完面试复盘,
I want 看到按维度拆分的评分（技术深度、表达结构、STAR完整度，以及在有 JD 匹配时的 JD 相关度）,
so that 我能精准定位自己的薄弱点，而不是只看一个笼统的总分。

## Acceptance Criteria

1. **后端结构化输出**：`POST /api/practice/analyze` 响应中 `analysis_json` 新增 `dimensions` 数组字段，每项包含 `name`、`score`（0-100）、`comment` 字段
2. **维度数量动态**：当请求中未传 `jd_context`（无 active JD）时，`dimensions` 只包含 3 个维度（不含"JD 相关度"）；有 JD 时包含 4 个维度
3. **向后兼容**：原有 `score`、`strengths`、`weaknesses`、`overall_feedback` 字段保持不变，`dimensions` 为新增字段
4. **前端展示**：`EvaluationCard` 展示各维度名称 + progress-bar + AI 点评；`dimensions` 为空数组时降级展示（只显示总分）
5. **API 类型同步**：前端 TypeScript 类型更新，包含 `Dimension` interface

## Tasks / Subtasks

- [ ] **Task 1: 更新 interview_review.py prompt** (AC: #1, #2)
  - [ ] 打开 `backend/interview_review.py`，修改 `_USER` prompt 模板
  - [ ] 在现有 4 个评估要求后追加维度评分要求：
    ```
    5. 按以下维度分别打分（每个维度 0-100 分，附 1-2 句点评）：
       - 技术深度：技术概念是否准确、有深度
       - 表达结构：逻辑是否清晰、有条理
       - STAR 完整度：是否包含情境/任务/行动/结果
       {jd_dimension}
    ```
  - [ ] 在函数参数中增加 `has_jd: bool = False`，控制是否注入 "JD 相关度" 维度
  - [ ] 更新 JSON 输出 schema，新增 `dimensions` 字段：
    ```json
    "dimensions": [
      {"name": "技术深度", "score": 75, "comment": "点评"},
      {"name": "表达结构", "score": 80, "comment": "点评"},
      {"name": "STAR完整度", "score": 60, "comment": "点评"}
    ]
    ```
  - [ ] 更新 `parse_json_response` 后的 `setdefault`，加 `result.setdefault("dimensions", [])`

- [ ] **Task 2: 更新 practice_service.py + practice router** (AC: #2, #3)
  - [ ] `backend/services/practice_service.py:analyze_answer()`：新增 `has_jd: bool = False` 参数，透传给 `analyze_single_qa`
  - [ ] `backend/routers/practice.py:analyze_answer()`（约 line 27）：
    - 检查 `req.profile_id` 对应的 profile 是否有关联的 active JD diagnosis
    - 查询 `JdDiagnosis` 表：`db.query(JdDiagnosis).filter(JdDiagnosis.profile_id == profile_id).order_by(JdDiagnosis.created_at.desc()).first()`
    - 如有结果则 `has_jd = True`，传给 `practice_svc.analyze_answer()`
  - [ ] 确认 `analysis_json` 字段 JSON 序列化包含 `dimensions` 数组

- [ ] **Task 3: 更新前端 TypeScript 类型** (AC: #5)
  - [ ] 在 `frontend/src/types/practice.ts` 或相关类型文件中新增：
    ```typescript
    export interface Dimension {
      name: string
      score: number   // 0-100
      comment: string
    }
    export interface EvaluationResult {
      // 已有字段保持不变
      score: number
      overall_feedback: string
      strengths: { point: string; detail: string }[]
      weaknesses: { point: string; suggestion: string }[]
      // 新增
      dimensions: Dimension[]
    }
    ```

- [ ] **Task 4: 更新 EvaluationCard 前端组件** (AC: #4)
  - [ ] 打开 `frontend/src/components/practice/EvaluationCard.tsx`
  - [ ] 在总分展示下方，当 `result.dimensions.length > 0` 时渲染维度区块：
    - 区块标题："维度分析"
    - 每个维度：`名称 | progress-fill bar（宽度 = score%）| score 分 | comment 文字`
    - 使用已有的 `progress-track` / `progress-fill` CSS class（index.css 已定义）
  - [ ] 当 `dimensions` 为空或 undefined 时，降级：只显示原有总分 + strengths/weaknesses，不报错

## Dev Notes

### 关键文件路径

| 文件 | 改动内容 |
|------|----------|
| `backend/interview_review.py` | prompt 扩展 + `has_jd` 参数 + dimensions schema（line 19-99） |
| `backend/services/practice_service.py` | `analyze_answer()` 透传 `has_jd`（line 19-33） |
| `backend/routers/practice.py` | 查询 active JD，构造 `has_jd` flag（line 27-65） |
| `frontend/src/types/practice.ts` | 新增 `Dimension` interface，更新 `EvaluationResult` |
| `frontend/src/components/practice/EvaluationCard.tsx` | 渲染 dimensions 区块 |

### 设计决策（已与 PM/Analyst 确认）

- **无 JD 时**：`dimensions` 包含 3 项（不含"JD 相关度"），前端**不显示**"JD 相关度"维度，不显示 N/A
- **向后兼容**：`dimensions: []` 时前端降级展示，不 breaking 已有功能
- **数据源**：`has_jd` 通过查询最近一次 JdDiagnosis 判断，无需前端传参

### 维度评分的 JSON Schema（最终定稿，Winston 确认）

```typescript
interface AnalysisResult {
  score: number           // 总分 0-100（保持）
  overall_feedback: string
  strengths: { point: string; detail: string }[]
  weaknesses: { point: string; suggestion: string }[]
  dimensions: Dimension[] // 新增，无 JD 时 3 项，有 JD 时 4 项
}

interface Dimension {
  name: string    // "技术深度" | "表达结构" | "STAR完整度" | "JD相关度"
  score: number   // 0-100
  comment: string // 1-2 句 AI 点评
}
```

### CSS 参考

`index.css` 中已定义（无需新增样式）：
```css
.progress-track { height: 6px; border-radius: 100px; background: rgba(255,255,255,0.35); }
.progress-fill  { background: linear-gradient(90deg, #2563EB, #60a5fa); }
```

### References

- `backend/interview_review.py` — `_USER` prompt + `analyze_single_qa()` [line 19-99]
- `backend/services/practice_service.py` — `analyze_answer()` [line 19-33]
- `backend/routers/practice.py` — analyze endpoint [line 27-65]
- `frontend/src/components/practice/EvaluationCard.tsx` — 渲染组件

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List
