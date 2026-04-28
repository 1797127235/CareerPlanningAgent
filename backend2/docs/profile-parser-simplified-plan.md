# 简历解析与画像建立重构方案

本文档是 `backend2` 中“简历解析 -> 画像建立”模块的当前执行方案。

核心目标不是把解析链路做得更复杂，而是把边界收窄：**简历解析只产出事实画像，不产出职业判断**。

> 本方案替代旧版“多 ParseStrategy + merger + normalizer”的设计思路。ResumeSDK 不再作为平级解析策略，merger 不再负责字段级优先级合并，normalizer 不再维护职业语义规则。

参考 `E:\OpenHub\Resume-Matcher` 后，本方案补充三条工程约束：

- 原始文本优先保留为 Markdown，因为 Markdown 比纯文本更能保留章节、列表和日期上下文。
- LLM JSON 输出必须经过稳定解析、重试和 Pydantic schema 校验。
- Postprocess 可以做“事实保真”修复，例如恢复 LLM 丢失的日期月份，但不能做职业判断。

## 1. 设计原则

### 1.1 Parser 只做事实提取

Parser 层只回答一个问题：

> 这份简历里明确写了什么？

它可以提取：

- 姓名
- 求职意向原文
- 教育经历
- 技能
- 项目经历
- 实习经历
- 奖项证书
- 原始文本

它不应该判断：

- 候选人最适合哪个岗位方向
- 技能属于哪个岗位图谱节点
- 公司属于什么 tier
- 候选人偏研究还是偏工程
- 应该推荐哪些职位
- 最终职业路径是什么

这些判断属于后续的岗位图谱、职位评估、报告生成模块。

### 1.2 LLM 是唯一语义解析器

LLM 负责语义工作：

- 字段提取
- 技能名称标准化
- 重复内容合并
- 无意义内容过滤
- 根据 raw_text 和可选证据生成 `ProfileData`

代码层不维护技能别名表、岗位方向枚举、公司层级表、字段来源优先级。

### 1.3 ResumeSDK 是证据，不是最终解析源

ResumeSDK 如果启用，只提供辅助证据：

```text
ResumeFile + ResumeDocument
  -> ResumeSDKEvidenceProvider
  -> resumesdk_evidence
  -> LLMParser
```

最终 `ProfileData` 仍由 LLM 基于 `raw_text + evidence` 生成。

这样可以避免：

- ResumeSDK 和 LLM 产生两个并列画像
- 字段级优先级合并
- `name 用 SDK，skills 用 LLM` 这类规则
- ResumeSDK 失败导致主流程失败

### 1.4 保留系统边界规则

本方案反对的是“职业知识硬编码”，不是反对所有规则。

应该保留的系统规则：

- 文件大小限制
- 文件类型校验
- raw_text 必须保留
- raw_text 优先保留 Markdown 格式
- Pydantic schema 校验
- 空值清理
- 列表去重
- 日期精度保真
- 解析失败 warning
- 质量评分

应该移除的职业语义规则：

- `js -> JavaScript` 这类技能别名表
- `Spring Boot` 存在就删除 `Spring`
- `primary_domain` 枚举
- `career_signals` 推理
- 公司 tier 规则
- 研究/工程倾向判断
- SDK/LLM 字段优先级表

## 2. 目标流程

```text
前端上传简历文件
  -> Router 校验文件大小和类型
  -> ProfileService.parse_resume_preview()
  -> ResumeFile
  -> ExtractorRegistry 提取 raw_text/markdown
  -> ResumeDocument(raw_text, text_format)
  -> 可选 ResumeSDK evidence
  -> LLMParser.parse(document, evidence)
  -> ProfileData
  -> Postprocess 防御性清理 + 事实保真修复
  -> Quality 质量评分
  -> ParseResumePreviewResponse
  -> 前端预览
  -> 用户确认后保存 Profile
```

第一阶段只实现“解析预览”。保存、岗位图谱映射、报告生成不要混进 parser。

## 3. 目录结构

建议将 `backend2/services/profile` 收敛为：

```text
backend2/
  schemas/
    profile.py

  services/
    profile/
      service.py

      parser/
        pipeline.py
        llm_parser.py
        prompts.py
        postprocess.py
        quality.py

        extractors/
          __init__.py
          registry.py
          markitdown.py
          txt.py
          docx.py
          pdf.py
          ocr.py

        evidence/
          __init__.py
          resumesdk.py

  routers/
    profiles.py
```

建议逐步移除或降级：

```text
services/profile/parser/strategies/
services/profile/parser/merger.py
services/profile/parser/normalizer.py
```

其中：

- `strategies/` 删除：不再维护多个平级解析源。
- `merger.py` 删除：最终只有一个 LLM 生成的 `ProfileData`。
- `normalizer.py` 降级/改名为 `postprocess.py`：只做非语义清理。

## 4. 核心契约

### 4.1 ResumeFile

`ResumeFile` 是内部输入对象，不入库，不返回前端。

```python
class ResumeFile(BaseModel):
    filename: str
    content_type: str | None = None
    file_bytes: bytes = Field(exclude=True)
```

用途：

- 给 extractor 提取文本
- 给 ResumeSDK evidence provider 调用第三方接口

不要把 `file_bytes` 放进 `ResumeDocument`。`ResumeDocument` 应该只表达“文本提取结果”，不应该暗含原始二进制文件。

### 4.2 ResumeDocument

`ResumeDocument` 表示提取后的文档文本。

```python
class ResumeDocument(BaseModel):
    filename: str
    content_type: str | None = None
    raw_text: str
    text_format: Literal["plain", "markdown"] = "plain"
    extraction_method: str
    ocr_used: bool = False
    warnings: list[str] = []
```

要求：

- `raw_text` 必须完整保留。
- 优先保存 Markdown；只有确实无法保留结构时才退化为 plain text。
- `text_format` 用于告诉后续 LLMParser 当前文本是 Markdown 还是纯文本。
- OCR 只是文本提取层的 fallback。
- document 不负责画像字段。

### 4.3 ProfileData

`ProfileData` 是简历事实画像。

建议字段：

```python
class ProfileData(BaseModel):
    name: str = ""
    job_target_text: str = ""
    domain_hint: str = ""
    education: list[Education] = []
    skills: list[Skill] = []
    projects: list[Project] = []
    internships: list[Internship] = []
    awards: list[str] = []
    certificates: list[str] = []
    raw_text: str = ""
```

字段说明：

- `job_target_text`：简历中写明的求职意向原文，不是系统推断岗位。
- `domain_hint`：LLM 给出的弱提示，可用于前端预览，但不能作为最终职位评估结论。
- `raw_text`：为兼容和追溯可暂时保留在 ProfileData 中；后续也可以单独持久化到 resume_documents 表。

不建议放在 parser 核心输出中：

- `primary_domain`
- `career_signals`
- `research_vs_engineering`
- `internship_company_tier`
- `recommended_roles`
- `matched_graph_nodes`

这些属于后续图谱映射和职位评估层。

### 4.4 ParseMeta

`ParseMeta` 描述本次解析过程。

```python
class ParseMeta(BaseModel):
    llm_model: str = ""
    evidence_sources: list[str] = []
    json_repaired: bool = False
    retry_count: int = 0
    quality_score: int = 0
    quality_checks: dict[str, bool] = {}
    warnings: list[str] = []
```

用途：

- 前端展示解析质量
- 调试 ResumeSDK/OCR/LLM 调用情况
- 记录 LLM JSON 是否经历重试或修复
- 为后续用户反馈和重解析留入口

### 4.5 ParseResumePreviewResponse

`ParseResumePreviewResponse` 是解析预览接口返回值。

```python
class ParseResumePreviewResponse(BaseModel):
    profile: ProfileData
    document: ResumeDocument
    meta: ParseMeta
```

第一阶段不建议在该响应里返回报告、岗位推荐、图谱匹配结果。

## 5. 模块职责

### 5.1 Router

`routers/profiles.py` 只负责 HTTP 边界：

- 接收上传文件
- 校验文件大小
- 校验文件类型
- 调用 `ProfileService`
- 返回 response schema

Router 不应该：

- 判断是否 OCR
- 调用 ResumeSDK
- 拼 prompt
- 合并画像字段
- 计算职业方向

### 5.2 ProfileService

`ProfileService` 是业务入口。

第一阶段建议只提供：

```python
parse_resume_preview(file: UploadFile) -> ParseResumePreviewResponse
```

后续再扩展：

```python
save_profile(user_id, profile)
get_profile(user_id)
update_profile(user_id, patch)
```

Service 负责把 HTTP 文件转换为 `ResumeFile`，并调用 parser pipeline。

### 5.3 ParserPipeline

`ParserPipeline` 负责流程编排：

```text
ResumeFile
  -> extract ResumeDocument
  -> collect evidence
  -> LLM parse ProfileData
  -> postprocess
  -> quality score
  -> response parts
```

它不写职业规则，也不持久化数据库。

### 5.4 Extractors

Extractor 只负责提取可读文本：

- markitdown
- txt
- docx
- pdf
- ocr

建议优先尝试把 PDF/DOCX 转成 Markdown。Markdown 能保留标题、列表、日期附近的上下文，通常比纯文本更适合作为 LLM 输入。

OCR 是 PDF 文本提取失败或文本过短时的 fallback。OCR 得到的文本一般标记为 `text_format="plain"`。

Extractor 不应该生成画像字段。

### 5.5 Evidence Provider

第一阶段只有 ResumeSDK：

```text
ResumeSDKEvidenceProvider.collect(file, document) -> dict | None
```

要求：

- 没配置时跳过。
- 调用失败时返回 warning，不中断主流程。
- 返回值只进入 LLM prompt，不直接成为最终 ProfileData。

后续可以增加其他 evidence provider，例如：

- 第三方简历解析 API
- 学历认证接口
- GitHub/LinkedIn 补充信息

但它们仍然只是证据，不直接决定最终画像。

### 5.6 LLMParser

LLMParser 是唯一语义解析器：

```text
LLMParser.parse(document, evidence) -> ProfileData
```

Prompt 需要强调：

- 以 `raw_text` 为准。
- evidence 只是参考。
- 输出必须符合 `ProfileData` schema。
- 技能使用行业标准写法。
- 去除重复项、空项和明显无意义内容。
- 不要做岗位图谱映射。
- 不要生成职位推荐。

如果主解析没有提取出 skills，可以保留一次轻量 `skill_retry`，但它仍然属于 LLMParser 内部逻辑，不变成独立 strategy。

LLM JSON 解析需要做成稳定能力，而不是简单 `json.loads()`：

- 如果模型支持 JSON mode，优先使用 JSON mode。
- 清理 markdown code block。
- 清理 thinking/reasoning tag。
- 检测明显截断的 JSON。
- JSON 解析失败时允许有限次数重试。
- 最终必须经过 `ProfileData.model_validate()`。

这部分可以参考 Resume-Matcher 的 `complete_json()` 思路，但要收敛到 `backend2/llm/client.py` 或 `parser/llm_parser.py`，不要散落到 Router。

### 5.7 Postprocess

`postprocess.py` 只做非语义清理：

- 字符串 `strip`
- 列表去空
- 列表去重
- 删除 `company` 和 `role` 同时为空的 internship
- 强制回填 `raw_text`
- 保留日期原始精度；如果 LLM 把 `2024.03 - 2024.08` 简化成 `2024 - 2024`，可以从 raw_text/markdown 中恢复
- 保证字段符合 schema 默认值

它不做：

- 技能别名归一化
- 岗位方向映射
- 公司层级判断
- 职业信号推理

### 5.8 Quality

质量评分只评估结构完整性，不判断用户好坏。

建议检查项：

```text
has_name
has_job_target_text
has_education
has_skills
has_projects
has_internships
has_raw_text
```

返回：

```python
{
    "score": 71,
    "checks": {
        "has_name": True,
        "has_skills": True,
        "has_projects": False
    }
}
```

不要在 parser 层定义“多少分通过”。前端可以展示完整度，下游模块可以自行决定是否需要提醒用户补充信息。

## 6. Resume-Matcher 对照结论

`E:\OpenHub\Resume-Matcher` 的简历解析链路可以总结为：

```text
Upload PDF/DOCX
  -> validate file
  -> MarkItDown 转 Markdown
  -> 保存 original_markdown
  -> LLM parse Markdown to JSON
  -> Pydantic schema validate
  -> ready/failed status
```

我们吸收其中三点：

- **原始 Markdown 长期保存**：不要只保存 LLM 解析后的结构化结果，后续重解析、日期修复、报告生成都需要原始文本。
- **schema 驱动解析**：prompt 给出目标 schema，LLM 输出后必须由 Pydantic 校验。
- **事实保真 postprocess**：可以修复 LLM 丢失的事实细节，例如日期月份，但不能引入职业判断。

我们不照搬其中三点：

- Router 里直接做解析、保存、LLM 调用。`backend2` 仍然要通过 `ProfileService + ParserPipeline` 保持薄 Router。
- 直接复用它的 `ResumeData` schema。它偏简历编辑器，我们需要的是职业画像事实契约。
- 只依赖 MarkItDown。`backend2` 仍保留 OCR fallback 和 ResumeSDK evidence provider。

## 7. Prompt 边界

主 prompt 应该聚焦事实提取。

允许：

```text
请提取简历中明确出现的信息。
技能请使用常见行业标准名称。
去除重复、空值、明显无意义内容。
如果提供 ResumeSDK evidence，可以参考，但 raw_text 优先。
domain_hint 只是粗略提示，不是最终职业方向。
```

禁止：

```text
请判断候选人最适合哪个岗位图谱节点。
请根据公司 tier 评价实习含金量。
请输出 career_signals。
请判断研究型/工程型。
请推荐岗位。
```

## 8. 与后续模块的关系

简历解析完成后，后续模块应该从 `ProfileData` 读取事实，再做自己的判断。

推荐后续分层：

```text
ProfileData
  -> ProfileToGraphMapper
  -> SkillResolver
  -> JobRoleMatcher
  -> JDEvaluator
  -> ReportGenerator
```

其中：

- `SkillResolver` 可以使用岗位图谱技能库做标准名匹配。
- `ProfileToGraphMapper` 可以把技能、项目、经历映射到岗位图谱。
- `JDEvaluator` 可以结合 JD 判断匹配度。
- `ReportGenerator` 可以解释优势、短板和下一步建议。

这些逻辑不要反向塞进 parser。

## 9. 第一阶段落地顺序

建议按以下顺序改：

1. 固定 `schemas/profile.py` 契约：`ResumeFile`、`ResumeDocument`、`ProfileData`、`ParseMeta`、`ParseResumePreviewResponse`。
2. 给 `ResumeDocument` 增加 `text_format`，并明确 raw_text 优先保存 Markdown。
3. 新建或收敛 `ProfileService.parse_resume_preview()`。
4. 改造 `parser/pipeline.py` 为单 LLM 路径。
5. 将 ResumeSDK 移到 `parser/evidence/resumesdk.py`。
6. 将 `normalizer.py` 降级为 `postprocess.py`，只保留非语义清理和事实保真修复。
7. 删除 `merger.py` 的字段优先级合并逻辑。
8. 删除 `strategies/` 或停止从主流程引用。
9. 新建 `quality.py`，返回结构完整度评分。
10. 强化 LLM JSON 解析：JSON mode、代码块清理、截断检测、有限重试、schema validate。
11. 接入 `routers/profiles.py` 的解析预览接口。
12. 补测试：普通文本、docx、PDF、扫描件、ResumeSDK 失败、LLM 空结果、raw_text 保留、日期精度保真。

## 10. 验收标准

第一阶段完成后，应满足：

- 上传简历后可以返回稳定的 `ParseResumePreviewResponse`。
- `raw_text` 永不丢失，且 PDF/DOCX 优先保留 Markdown。
- `ResumeDocument.text_format` 能明确标识 `plain` 或 `markdown`。
- ResumeSDK 未配置或失败时，LLM 仍能解析。
- Parser 不再依赖岗位图谱。
- Parser 不输出强职业判断字段。
- 没有字段级 SDK/LLM 合并规则。
- 没有技能别名硬编码表。
- LLM 输出必须经过 JSON 稳定解析和 Pydantic schema 校验。
- postprocess 只做非语义清理和事实保真修复。
- Router 不包含 OCR、ResumeSDK、prompt、职业判断逻辑。
- 后续职位评估和报告生成只依赖 `ProfileData`，不依赖 parser 内部实现。

## 11. 暂不做的事

第一阶段不要做：

- 岗位图谱映射
- JD 匹配
- 报告生成
- 多 Agent 编排
- LangGraph 工作流
- 复杂技能知识库
- 用户长期画像演化
- 多版本画像合并

原因是当前最重要的是把基础画像解析链路做稳定、清晰、可替换。等 `ProfileData` 契约稳定后，再向职位评估和报告生成扩展。
