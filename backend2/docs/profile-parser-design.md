# Backend2 Profile Parser 设计指导

本文档用于指导 `backend2` 中“简历解析 -> 用户画像建立”的重构。目标不是一次性把所有能力做复杂，而是先把边界、契约和可插拔点定清楚，让后续替换 ResumeSDK、增加 OCR、增加新的解析工具时不牵动业务主流程。

## 1. 设计目标

本模块只解决一件事：

> 输入一份简历文件，稳定产出一份标准化的用户画像，并且完整保留原始文本。

核心要求：

- 解析策略可插拔：ResumeSDK、LLM Direct、未来第三方工具都可以替换。
- 原始文本必须保留：不管哪个策略成功，`raw_text` 都不能丢。
- Router 不参与解析细节：接口层只负责鉴权、文件校验、调用 service。
- 策略之间互不依赖：ResumeSDK 挂了不能影响 LLM direct。
- 合并逻辑集中：字段优先级、冲突处理、去重规则不能散落在策略里。
- 输出契约稳定：下游 JD 评估、报告、面试准备只依赖标准画像。

## 2. 推荐目录结构

```text
backend2/
  services/
    profile/
      parser/
        __init__.py
        pipeline.py
        base.py
        extractors/
          __init__.py
          base.py
          pdf_text.py
          docx_text.py
          txt_text.py
          ocr_vlm.py
        strategies/
          __init__.py
          resumesdk.py
          llm_direct.py
        normalizer.py
        merger.py
      profile_service.py
  schemas/
    profile.py
  routers/
    profiles.py
```

说明：

- `pipeline.py`：唯一编排入口，负责调度 extractor、strategy、normalizer、merger。
- `base.py`：定义策略接口，公共数据结构从 `schemas/profile.py` 引入。
- `extractors/`：负责把不同文件变成 `raw_text`。
- `strategies/`：负责把 `raw_text` 解析成画像候选结果。
- `merger.py`：负责多个候选结果的字段级合并。
- `normalizer.py`：负责技能别名、字段清洗、去重。
- `profile_service.py`：负责画像业务，如保存、更新、质量评分。
- `routers/profiles.py`：只暴露 HTTP API，不写解析分支。

## 2.1 schemas 的边界

`schemas/` 是 `backend2` 的公共契约层，不是 parser 的私有类型目录。

```text
routers/   处理 HTTP 请求和响应
services/  承担业务流程
schemas/   定义跨模块输入输出契约
db/        定义 ORM 模型和存储访问
graphs/    编排 services，不定义业务数据
```

因此，凡是会被多个模块依赖的数据结构，都应该放在 `backend2/schemas/`：

```text
backend2/schemas/
  common.py        # APIResponse / ErrorResponse / Pagination
  profile.py       # ProfileData / ResumeDocument / ParseCandidate
  opportunity.py   # OpportunityEvaluation / MatchScore / GapItem
  growth_plan.py   # GrowthPlan / ActionItem
  evidence.py      # EvidenceItem / EvidenceSummary
  interview_prep.py
  report.py
```

`services/profile/parser/` 内部只放解析流程的实现细节：

```text
parser/base.py
  TextExtractor
  ParseStrategy

parser/strategies/resumesdk.py
  ResumeSDK 私有响应结构
  ResumeSDK 到 ProfileData 的适配逻辑
```

也就是说：

- `ProfileData` 不应该藏在 `parser/schema.py`。
- `ResumeDocument` 不应该藏在 extractor 里。
- `ParseCandidate` 不应该只属于某一个 strategy。
- ResumeSDK 原始返回结构、LLM prompt 中间结构可以留在 strategy 内部。

原因是 `ProfileData` 后续会被 Opportunity Evaluation、Growth Plan、Interview Prep、Report 共同依赖。如果它放在 parser 内部，下游模块就会反向依赖解析器，边界会再次变乱。

## 3. 核心流程

```text
UploadFile
  -> ProfileRouter
  -> ProfileService.parse_resume()
  -> ResumeParserPipeline.parse()
  -> ExtractorRegistry.extract()
  -> raw_text
  -> ParseStrategy[]
  -> ParseCandidate[]
  -> ProfileMerger.merge()
  -> ProfileNormalizer.normalize()
  -> ProfileData
  -> ProfileService.save_or_preview()
```

第一阶段建议只做两个接口：

```text
POST /api/v2/profiles/parse-resume
PUT  /api/v2/profiles
```

其中：

- `parse-resume`：只解析，不保存，用于前端预览。
- `PUT /profiles`：保存或合并画像。

不要在第一阶段把报告生成、JD 评估、面试准备塞进画像解析流程。画像是基础资产，下游模块只读取画像，不反向污染画像解析。

## 4. 数据契约

### 4.1 ResumeDocument

`ResumeDocument` 表示“原始简历文档解析上下文”，它应该成为一等对象，而不是藏在 `ProfileData.raw_text` 里。

建议字段：

```python
class ResumeDocument(BaseModel):
    filename: str
    content_type: str | None = None
    raw_text: str
    extractor: str
    is_scanned: bool = False
    warnings: list[str] = []
```

注意：

- `raw_text` 保存完整文本。
- 不建议在 pipeline 层直接截断 `raw_text`。
- 如果 LLM prompt 需要截断，只在 LLM strategy 内部生成 `prompt_text`。
- 持久化时可以单独保存 `raw_text`，画像里只保留引用。

### 4.2 ProfileData

`ProfileData` 是下游模块依赖的标准画像契约。

建议第一阶段只保留稳定字段：

```python
class ProfileData(BaseModel):
    name: str = ""
    job_target: str = ""
    primary_domain: str = ""
    education: Education = Education()
    skills: list[Skill] = []
    knowledge_areas: list[str] = []
    internships: list[Internship] = []
    projects: list[str] = []
    awards: list[str] = []
    certificates: list[str] = []
    career_signals: CareerSignals = CareerSignals()
    soft_skills: dict = {}
    source_document_id: int | None = None
```

`raw_text` 可以为了兼容旧前端暂时保留，但在 `backend2` 的设计上不要把它当成画像本体。

### 4.3 ParseCandidate

策略不要直接返回最终画像，应该返回候选结果。

```python
class ParseCandidate(BaseModel):
    source: str
    profile: ProfileData
    confidence: float = 0.0
    raw_output: dict | None = None
    warnings: list[str] = []
```

这样做的好处：

- 可以知道每个字段来自哪个策略。
- merger 可以按来源优先级合并。
- 调试时能看到 ResumeSDK 和 LLM 分别输出了什么。
- 开源后别人更容易定位解析失败原因。

## 5. 插拔接口

### 5.1 Extractor

Extractor 只做一件事：把文件转换成原始文本。

```python
class TextExtractor(ABC):
    name: str

    @abstractmethod
    def supports(self, filename: str, content_type: str | None) -> bool:
        ...

    @abstractmethod
    def extract(self, file_bytes: bytes, filename: str) -> ResumeDocument | None:
        ...
```

推荐执行顺序：

```text
txt -> docx -> pdf_text -> ocr_vlm
```

扫描件 PDF 不应该在 router 里特殊处理，而应该由 extractor 层识别并 fallback 到 OCR。

### 5.2 ParseStrategy

ParseStrategy 只做一件事：从 `ResumeDocument` 中提取结构化画像候选结果。

```python
class ParseStrategy(ABC):
    name: str

    @abstractmethod
    def parse(self, document: ResumeDocument) -> ParseCandidate | None:
        ...
```

第一阶段策略：

```text
ResumeSDKStrategy
LLMDirectStrategy
```

推荐默认顺序：

```python
strategies = [
    ResumeSDKStrategy(),
    LLMDirectStrategy(),
]
```

不要让 `ResumeSDKStrategy` 内部调用 `LLMDirectStrategy`。如果 ResumeSDK 输出需要 LLM 适配，可以把它视为 ResumeSDK 策略内部的实现细节，但它返回的 `source` 仍然应该标记清楚，例如 `resumesdk_llm_adapter`。

## 6. 合并规则

合并应该集中在 `merger.py`。

建议第一阶段规则：

| 字段 | 优先级 |
| --- | --- |
| `name` | ResumeSDK 优先，LLM 兜底 |
| `education` | ResumeSDK 优先，LLM 兜底 |
| `job_target` | 原文正则 hint + LLM 优先 |
| `primary_domain` | LLM 优先 |
| `skills` | 多来源合并，别名归一后去重 |
| `projects` | LLM 优先，ResumeSDK 补充 |
| `internships` | 公司 + 岗位去重，信息更完整者优先 |
| `awards/certificates` | 多来源合并 |
| `career_signals` | LLM 优先 |

merger 的输入应该是列表：

```python
def merge_candidates(
    candidates: list[ParseCandidate],
    document: ResumeDocument,
) -> ProfileData:
    ...
```

不要只设计成 `merge_profiles(sdk, llm)`，否则以后加第三个策略会继续改主流程。

## 7. raw_text 保留原则

这是本模块最重要的原则之一。

规则：

- extractor 产出的 `raw_text` 是完整文本。
- strategy 可以在内部截断 prompt，但不能覆盖 document 的完整 `raw_text`。
- merger 不负责截断 `raw_text`。
- 保存画像时，要能追溯到原始文本。
- 重新解析必须基于保存的完整 `raw_text`，不能基于截断后的字段。

推荐持久化方式：

```text
profiles
  id
  user_id
  profile_json
  quality_json
  source_document_id

resume_documents
  id
  user_id
  filename
  raw_text
  extractor
  parse_meta_json
  created_at
```

如果第一阶段不想建新表，也至少要在 `profile_json` 里保留完整 `raw_text`，不要在 pipeline 中截断。

## 8. Router 边界

`routers/profiles.py` 只允许做这些事：

- 鉴权。
- 文件大小和类型校验。
- 调用 `ProfileService`。
- 返回统一响应。

不应该做这些事：

- 判断扫描件。
- 决定使用 ResumeSDK 还是 LLM。
- 写 `_extract_profile_with_llm`。
- 直接调用 OCR。
- 直接合并 profile 字段。
- 直接计算复杂画像逻辑。

目标是让 router 变成这样：

```python
@router.post("/parse-resume")
async def parse_resume(file: UploadFile, user=Depends(get_current_user)):
    file_bytes = await file.read()
    result = profile_service.parse_resume_preview(
        user_id=user.id,
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type,
    )
    return ok(result)
```

## 9. 第一阶段落地顺序

建议不要一口气做完整重构，按这个顺序推进：

1. 定义 `schemas/profile.py`：先确定 `ProfileData`、`ResumeDocument`、`ParseCandidate`。
2. 新建 `parser/base.py`：定义 `TextExtractor` 和 `ParseStrategy`。
3. 新建 `parser/pipeline.py`：实现主流程，但先用 mock strategy 跑通。
4. 搬迁现有 `text_extractor.py` 到 `extractors/`。
5. 搬迁 ResumeSDK 调用到 `strategies/resumesdk.py`。
6. 搬迁 LLM 直接解析到 `strategies/llm_direct.py`。
7. 改造 `merger.py`：从二源合并升级为多候选合并。
8. 改造 `normalizer.py`：集中做技能别名、空字段清理、列表去重。
9. 新建 `ProfileService.parse_resume_preview()`。
10. 最后再接 `routers/profiles.py`。

每一步都要能单独跑测试，不要等所有文件都搬完再验证。

## 10. 最小测试用例

第一阶段至少要覆盖：

- 普通文本简历可以提取 `raw_text`。
- PDF 文本简历可以提取 `raw_text`。
- 扫描件 PDF 在文本提取失败时进入 OCR extractor。
- ResumeSDK 失败时 LLM strategy 仍可工作。
- LLM 失败时如果 ResumeSDK 成功，仍返回画像。
- 所有策略失败时，仍返回包含 `raw_text` 的错误上下文。
- 合并后技能不重复。
- 合并后 `raw_text` 没有被截断。
- router 不直接调用任何具体 strategy。

## 11. 暂不做的事

为了避免第一阶段失控，暂时不要做：

- 不要把报告生成放进 parser。
- 不要把 JD 匹配放进 parser。
- 不要把 LangGraph 放进 parser。
- 不要在策略里写数据库保存。
- 不要让前端决定解析策略。
- 不要为了兼容所有历史字段把 `ProfileData` 做得过大。

## 12. 判断是否设计成功

当下面几件事成立时，说明这个模块边界基本收住了：

- 换掉 ResumeSDK 只需要新增一个 strategy 并改配置。
- OCR 从 VLM 换成本地 OCR 只需要新增 extractor。
- router 文件里看不到任何解析分支。
- 下游 JD 评估只读取 `ProfileData`，不关心简历怎么解析出来。
- 重新解析时可以基于完整 `raw_text` 执行。
- 单测可以不启动 FastAPI 就测试 parser pipeline。
