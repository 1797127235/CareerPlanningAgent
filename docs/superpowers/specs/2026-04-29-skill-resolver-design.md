# SkillResolver 设计文档

> SkillResolver v1 只做提及清洗，不做技能语义分层。

## 1. 背景与定位

### 1.1 为什么要有一层 Resolver

Parser（简历解析器）的职责是**忠实提取简历中明确出现的信息**。它不解释、不推断、不归类。

但真实简历中的技能/技术栈表述天然带有噪声：
- 版本号变体：`C++11`、`Python3.9`
- 标准库具体类名：`std::shared_ptr`、`std::unique_ptr`
- 项目内部类名：`EventLoop`、`TcpConnection`
- 别名/缩写：`js`、`ts`

这些词被 parser 正确抽取出来后，**需要一层轻量清洗**，才能进入下游的技能画像、岗位图谱、机会匹配等模块。

### 1.2 Parser 与 Resolver 的边界

| 层级 | 职责 | 不做的事 |
|---|---|---|
| **Parser** | 从简历文本中提取结构化事实 | 不解释技能含义，不做岗位映射，不判水平等级 |
| **Resolver** | 对 parser 输出的技能和 tech_stack 做准入清洗 | 不做技能分类、不做父子归并、不做岗位方向推断 |
| **下游图谱/评估** | 基于清洗后的画像做职业判断 | 不反向污染 parser 和 resolver |

### 1.3 第一版约束（硬性）

> **SkillResolver v1 只做提及清洗，不做技能语义分层。**

第一版允许的操作仅限三类：
1. **保留（keep）**——通用技术概念，原样保留
2. **折叠（fold）**——仅针对版本号变体和别名缩写，归并为标准写法
3. **删除（drop）**——项目内部符号、标准库具体类名、离开上下文无意义的词

第一版**明确不做**的操作：
- 子概念上卷到父概念（如"智能指针"→"C++"）
- 技能分类/层级判断
- 岗位方向推断
- 技能补全（简历没提到的技能不会凭空添加）

## 2. 核心契约

### 2.1 MentionRecord（输入）

Resolver 的输入不是"词表"，而是**带有上下文的 mention records**。每个 record 对应 ProfileData 中的一个具体出现位置。

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class MentionRecord:
    id: str
    """全局唯一标识，如 skill_3, proj_0_ts_5"""

    mention: str
    """原始词，如 EventLoop"""

    target_field: Literal["skills", "project.tech_stack", "internship.tech_stack"]
    """该 mention 最终要写入哪个字段。不同字段的准入标准不同。"""

    context: str
    """mention 出现的局部上下文。
    采样规则：
    1. 优先取 mention 所在行及相邻行
    2. 其次按句子窗口（前后各不超过1句）
    3. 整体截断到 300 字符，优先保留后半部分
    """

    source_name: str | None
    """如果 target_field 是 project/internship，填写来源项目/实习名称。"""
```

### 2.2 ResolverDecision（输出）

Resolver 对每个 mention 返回一条决策记录。

```python
@dataclass
class ResolverDecision:
    id: str
    """对应 MentionRecord.id"""

    mention: str
    """原始词（冗余，便于调试）"""

    decision: Literal["keep", "fold", "drop"]
    """准入决策"""

    canonical: str | None
    """标准写法。
    - keep / fold 时必填
    - drop 时为 null
    """

    reason_code: Literal[
        "general_tech_concept",
        "version_variant",
        "alias_variant",
        "project_internal_symbol",
        "standard_library_symbol",
        "too_context_specific",
        "ambiguous_keep",
        "ambiguous_drop",
    ]
    """决策原因枚举。系统逻辑只认 reason_code，不解析自由文本。"""

    reason_text: str
    """人可读的解释说明，用于调试和审计。"""

    confidence: float
    """置信度 0.0~1.0。v1 只记录，不参与业务逻辑。"""
```

### 2.3 ResolverResult（整体输出）

Resolver 不直接修改 ProfileData。它返回一个结果对象，由独立的 `apply_resolved_skills()` pure function 写回。

```python
from dataclasses import dataclass, field

@dataclass
class ResolverResult:
    decisions: list[ResolverDecision]
    """逐 mention 决策列表"""

    warnings: list[str]
    """处理过程中的警告信息"""

    resolver_version: str = "skill-resolver-v1"
    """版本标识"""

    summary: dict = field(default_factory=dict)
    """统计信息，如 keep/fold/drop 数量"""
```

## 3. 准入标准与 reason_code 定义

### 3.1 不同字段的准入差异

| target_field | 准入标准 |
|---|---|
| `skills` | 只收**跨项目可复用**的稳定技术概念。项目特有实现名、内部类名、架构角色名不能进。 |
| `project.tech_stack` | 收项目中实际使用的**通用技术概念**。如果某个技术只在特定项目语境下有意义（如 `EventLoop` 是项目内部类名），仍然 drop。但 `Reactor` 这种通用架构概念可以留。 |
| `internship.tech_stack` | 同 `project.tech_stack`。 |

### 3.2 reason_code / decision 组合表（v1）

| reason_code | 含义 | 允许 decision | 示例 |
|---|---|---|---|
| `general_tech_concept` | 通用技术概念 | `keep` | `epoll` → keep, `Linux` → keep |
| `version_variant` | 版本号变体 | `fold` | `C++11` → fold to `C++` |
| `alias_variant` | 别名/缩写 | `fold` | `js` → fold to `JavaScript` |
| `project_internal_symbol` | 项目内部符号/类名 | `drop` | `EventLoop` → drop |
| `standard_library_symbol` | 标准库具体类名/函数 | `drop` | `std::shared_ptr` → drop |
| `too_context_specific` | 离开特定上下文无意义 | `drop` | `ThreadCache`（某个项目内部机制）→ drop |
| `ambiguous_keep` | 模糊但倾向保留 | `keep` | `Reactor`（可能是通用模式，也可能是项目内部命名）→ keep |
| `ambiguous_drop` | 模糊但倾向删除 | `drop` | 无法识别的缩写或自定义符号 → drop |

### 3.3 关键判断原则

**"三问法"——看到每个词时依次问：**

1. 它是不是一个稳定的通用技术概念？
   - 是 → 可能保留（`general_tech_concept`）
2. 它是不是某个通用技能的具体写法或版本？
   - 是 → 折叠到标准写法（`version_variant` / `alias_variant`）
3. 它是不是离开这个项目上下文就没意义？
   - 是 → 直接剔除（`project_internal_symbol` / `too_context_specific`）

**第一版不做"子概念上卷"**

以下操作 v1 明确不做：
- `智能指针` → `C++`
- `Reactor` → `网络编程`
- `面向对象编程` → `C++`

这类"子概念归父概念"的动作已经进入语义解释层，不属于 v1 的清洗职责。

## 4. 数据流

```
PDF/DOCX → Extractor → LLM Parser → ProfileData
                                          ↓
                                   ┌──────────────┐
                                   │  收集阶段     │
                                   │  遍历 Profile  │
                                   │  生成 Mention  │
                                   │  Records      │
                                   └──────┬───────┘
                                          ↓
                                   ┌──────────────┐
                                   │  LLM Resolver │
                                   │  逐 mention   │
                                   │  决策         │
                                   └──────┬───────┘
                                          ↓
                                   ┌──────────────┐
                                   │  生成         │
                                   │ ResolverResult│
                                   └──────┬───────┘
                                          ↓
                                   ┌──────────────┐
                                   │  apply()      │
                                   │  写回 Profile │
                                   └──────┬───────┘
                                          ↓
                                   ProfileData（已清洗）
```

### 4.1 收集阶段

从 `ProfileData` 中提取所有需要清洗的 mention：

1. `profile.skills` 中的每个 `skill.name`
2. `profile.projects[].tech_stack` 中的每个词
3. `profile.internships[].tech_stack` 中的每个词

为每个 mention 生成 `MentionRecord`，包含局部上下文。**context 从 `ResumeDocument.raw_text` 中采样**，根据 mention 出现位置提取所在行/相邻行/句子窗口。

### 4.2 LLM 清洗阶段

将所有 MentionRecord 分批发给 LLM。LLM 返回每条 record 的 `ResolverDecision`。

**Batching 规则**
- 每批最多 **30 条 mention**
- 或每批总 context 字符数不超过 **8000 字符**（含 prompt 模板后接近模型上下文上限的 50%）
- 优先按同一 `target_field` 分组，减少字段切换带来的上下文干扰

**为什么不需要逐条发送？**
因为 resolver 的判断不依赖全局简历理解，只依赖局部上下文 + 通用技术知识。LLM 有能力在单轮对话中批量处理。Batching 是为了控制 token 消耗和延迟，不是改变逐条判断的语义。

### 4.3 写回阶段

调用方根据 `ResolverResult.decisions` 执行 `apply()`：

- `decision=keep` → 用 `canonical` 替换原词
- `decision=fold` → 用 `canonical` 替换原词
- `decision=drop` → 从对应字段删除该词

写回后，对每个字段内部再做一次去重（如 `project.tech_stack` 里可能出现两次 `C++`）。

## 5. 样例表

以下样例基于真实简历解析结果构造，用于验证契约的完备性和边界清晰度。

### 5.1 真实硬样例（争议小，可直接当规则参考）

| id | mention | target_field | source_name | context（截断） | decision | canonical | reason_code | reason_text | confidence |
|---|---|---|---|---|---|---|---|---|---|
| s0 | C++ | skills | — | 掌握 C/C++ 语言，深入理解面向对象编程思想 | keep | C++ | general_tech_concept | 通用编程语言 | 0.97 |
| s1 | C++11 | skills | — | 熟悉 C++11 现代语法特性，包括智能指针、lambda 表达式 | fold | C++ | version_variant | 语言版本号，归并到主语言 | 0.95 |
| s2 | js | skills | — | 熟练使用 js 进行前端开发，掌握 Vue 和 React 框架 | fold | JavaScript | alias_variant | 缩写，折叠为标准名 | 0.93 |
| s3 | std::shared_ptr | skills | — | 熟悉智能指针（如 std::shared_ptr、std::unique_ptr）的底层实现 | drop | null | standard_library_symbol | 标准库具体类名，不是独立技能 | 0.92 |
| s4 | EventLoop | project.tech_stack | C++高性能网络库 | 设计并实现 EventLoop + Channel + Poller 事件驱动架构 | drop | null | project_internal_symbol | 项目内部类名，离开本项目无意义 | 0.91 |
| s5 | epoll | project.tech_stack | C++高性能网络库 | 基于 epoll 完成 IO 多路复用，将底层网络事件与上层业务回调解耦 | keep | epoll | general_tech_concept | 通用 Linux 系统调用 | 0.94 |
| s6 | Reactor | project.tech_stack | C++高性能网络库 | 基于 Reactor 模式设计与实现高性能网络服务框架 | keep | Reactor | general_tech_concept | 通用设计模式/架构概念，非项目内部命名 | 0.86 |
| s7 | 对象池 | project.tech_stack | 高并发内存池 | 设计并实现对象分级与 Span 管理机制，引用对象池缓存 Span | keep | 对象池 | general_tech_concept | 通用设计模式 | 0.82 |
| s8 | 智能指针 | skills | — | 掌握 RAII 资源管理思想，熟悉智能指针 | keep | 智能指针 | general_tech_concept | 通用 C++ 技术概念 | 0.88 |

### 5.2 真实边界样例（用于说明裁决边界，不作为强规则样本）

> 以下样例中，e1 与 e3 的 confidence 低于 0.70；e2 虽高于 0.70，但仍作为边界争议样例保留，用于展示 `too_context_specific` 的裁决边界。它们的存在是为了展示 resolver 的裁决边界，不意味着 v1 已经能稳定处理这类 case。

| id | mention | target_field | source_name | context | decision | canonical | reason_code | reason_text | confidence |
|---|---|---|---|---|---|---|---|---|---|
| e1 | SQL | skills | — | 熟悉 MySQL 数据库，能使用 SQL 语句进行简单的增删查改 | keep | SQL | general_tech_concept | 在数据库工程师简历中 SQL 是独立技能；在本份 C++ 简历中偏向附属操作。v1 不做上下文深度推断，按通用概念保留 | 0.62 |
| e2 | 基数树 | project.tech_stack | 高并发内存池 | 采用基数树管理页映射关系，提升查找效率并减少内存碎片 | drop | null | too_context_specific | 内存池项目内部实现机制，非通用技术概念。此类底层数据结构名在 v1 中按上下文裁决，暂不保证跨项目一致性 | 0.78 |
| e3 | 数据结构与算法 | skills | — | 掌握常见的数据结构，并能进行简单的实现 | keep | 数据结构与算法 | ambiguous_keep | 表述偏宽泛，但简历明确列为独立技能板块，保留 | 0.68 |

### 5.3 合成兜底样例（非真实简历词，用于说明极端 fallback 策略）

| id | mention | target_field | source_name | context | decision | canonical | reason_code | reason_text | confidence |
|---|---|---|---|---|---|---|---|---|---|
| f1 | xx | skills | — | （parser 误抽出的无意义符号或无法识别的缩写） | drop | null | ambiguous_drop | 无法识别其通用技术含义，保守删除 | 0.55 |

> **说明**：`f1` 为合成样例，不代表任何真实简历中的词。用于说明当 parser 误抽出无意义符号时，resolver 应采取保守删除策略。

## 6. 与 Pipeline 的集成

### 6.1 集成点

```python
class ParserPipeline:
    def parse(self, file: ResumeFile) -> ParseResumePreviewResponse:
        # 1. 提取
        document = self.registry.extract(file)
        
        # 2. LLM 解析
        parse_result = llm_parse(document, evidence)
        profile = parse_result.profile
        
        # 3. 后处理
        profile = postprocess(profile, document)
        
        # 4. [新增] SkillResolver 清洗
        resolver = SkillResolver()
        resolver_result = resolver.resolve(profile, document)
        profile = apply_resolved_skills(profile, resolver_result)
        
        # 5. 质量评分
        quality_meta = score_profile(profile)
        ...
```

### 6.2 关键设计决策

**Resolver 放在 postprocess 之后、score_profile 之前**

原因：
- postprocess 做字段级清洗（strip、去重、删空）
- resolver 做语义级清洗（技能准入裁决）
- score_profile 基于最终清洗后的画像打分

**Resolver 的 LLM 调用使用轻量模型**

resolver 的 prompt 比 parser 短很多（只输入技能列表 + 局部上下文，不输入整份简历），可以使用更便宜的模型（如 qwen-turbo）来降低成本。

### 6.3 错误处理

- Resolver LLM 调用失败 → 记录 warning，返回原 ProfileData（不阻断）
- 部分 mention 决策失败 → 记录 warning，其余正常处理
- 所有决策 confidence 均低于阈值（v1 不启用阈值，只记录）→ 留待 v2 处理

## 7. 待办与 v2 展望

### v1 范围（当前设计）
- [ ] MentionRecord / ResolverDecision / ResolverResult 契约实现
- [ ] context 采样规则实现
- [ ] LLM Resolver prompt 编写
- [ ] apply() 写回逻辑实现
- [ ] 与 Pipeline 集成
- [ ] 单元测试覆盖 8 种 reason_code

### v2 可能方向（不在当前设计范围）
- confidence 阈值分流策略（高置信自动写回，低置信人工 review）
- 子概念上卷到父技能（如"智能指针"→"C++"）
- 技能图谱映射（如"epoll"→"Linux网络编程"）
- 多模型投票（轻量模型 + 强模型组合）

## 8. 附录：Prompt 模板（占位）

Resolver 的 LLM prompt 将在实现阶段单独编写，核心结构如下：

```
你是一个技能提及清洗 AI。

输入：一组 mention records，每条包含 mention、target_field、context。

任务：对每条 mention 做三选一决策：
- keep：通用技术概念，保留
- fold：版本号变体或别名缩写，归并为标准写法
- drop：项目内部符号、标准库具体类名、离开上下文无意义的词

第一版约束：
- 不做子概念上卷（如"智能指针"不要归到"C++"）
- 不做技能分类或岗位映射
- 只基于局部上下文判断，不推断简历整体方向

返回严格 JSON 数组，每条包含 id / decision / canonical / reason_code / reason_text / confidence。
```

详细 prompt 见实现文档。
