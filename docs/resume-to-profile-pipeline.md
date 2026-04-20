# 简历解析 → 画像生成 Pipeline 代码梳理

> 本文档梳理从简历上传、解析、画像构建、图谱定位到推荐生成的完整代码链路。
> 最后更新：2026-04-19

---

## 一、文件清单（按调用顺序）

```
backend/routers/profiles.py                 # API 入口 + 编排
backend/routers/_profiles_resumesdk.py      # ResumeSDK 商业解析器
backend/routers/_profiles_parsing.py        # LLM 解析 fallback + OCR
backend/routers/_profiles_helpers.py        # DB 操作 + 合并逻辑 + 序列化
backend/routers/_profiles_graph.py          # 图谱定位 + 推荐生成
backend/services/profile/
  ├── service.py                            # ProfileService facade
  ├── locator.py                            # 确定性图谱定位算法
  ├── scorer.py                             # 画像质量评分
  ├── sjt.py                                # SJT 题目生成
  ├── cooccurrence.py                       # 技能共现推断
  └── shared.py                             # 常量 + 权重表
backend/db_models.py                        # SQLAlchemy ORM 模型
agent/state.py                              # LangGraph 状态定义
```

---

## 二、完整数据流

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. 上传    POST /profiles/parse-resume                                    │
│     • 文件校验 (≤10MB, PDF/DOC/DOCX/TXT)                                   │
│     • 文本提取 (pdfplumber / python-docx / 直接解码)                        │
│     • 扫描版 PDF 检测 (无文字 → 走 OCR)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. 解析策略                                                                │
│     ├─ 文字版文件:                                                          │
│     │    parse_with_resumesdk()                                             │
│     │    • 调用阿里云 ResumeSDK API (JSON body + APPCODE)                   │
│     │    • 字段映射: 技能/学历/实习/项目/证书/职业信号                        │
│     │    • 质量门控: 0 技能 → 视为失败，fallback LLM                         │
│     │    • 技能补充: 从项目描述提取技术关键词回填                             │
│     │                                                                        │
│     └─ 扫描版 PDF:                                                          │
│          _ocr_pdf_with_vl()                                                 │
│          • 页面转图片 (300 DPI, 最多 5 页)                                   │
│          • 并行 OCR (qwen-vl-ocr)                                           │
│          • _extract_profile_with_llm(): 智能截断 + 结构化提取                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. LLM 提取  (_profiles_parsing.py)                                        │
│     • _RESUME_PARSE_PROMPT → 结构化 JSON                                    │
│       – name, job_target, primary_domain, career_signals, experience_years  │
│       – education, skills[{name, level}], knowledge_areas[]                 │
│       – internships[{company, role, duration, tech_stack, highlights}]      │
│       – projects[], awards[], certificates[]                                │
│     • 技能归一化: _SKILL_ALIASES (~80 条映射)                                │
│     • 后处理: 奖项迁移、实习校验降级、项目技能补充                             │
│     • 证书兜底: 正则匹配 CET-4/6、TOEFL、IELTS、软考等 30+ 证书              │
│     • 智能截断: _smart_truncate_resume() 保留高信号段落                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. 质量评分  (ProfileService.compute_quality)                               │
│     • 7 维度: skill_coverage, skill_depth, experience, education,           │
│       practice, certificates, competency                                    │
│     • 输出: completeness (0-1) + competitiveness (0-1) + dimensions          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. 预览响应  ({profile, quality})                                           │
│     • 不入库 — 前端展示供用户确认/编辑                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  6. 保存    PUT /profiles  (UpdateProfileRequest)                            │
│     • merge=True (简历上传) → _merge_profiles()                             │
│       – 技能: 并集，高等级覆盖低等级                                         │
│       – knowledge_areas / projects / awards: 集合去重并集                     │
│       – certificates: 按小写去重并集                                         │
│       – internships: 按 (company|role) 去重，新数据覆盖                       │
│       – education: 更丰富的保留                                              │
│       – experience_years: 取 max                                             │
│       – name: 非空则更新                                                     │
│       – raw_text: 总是覆盖为最新                                             │
│       – job_target / primary_domain: 新数据非空则覆盖                         │
│     • merge=False (手动编辑) → 完全替换                                      │
│     • profile_json + quality_json 存入 DB                                    │
│     • 启动后台线程: _auto_locate_on_graph()                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  7. 图谱定位 + 推荐  (后台线程)                                               │
│     a) embedding_prefilter()                                                │
│        • text-embedding-v4 余弦相似度，从 45 个节点预筛选 top 12-18           │
│     b) _llm_match_role()                                                    │
│        • LLM 读取候选节点列表 + 用户画像 → 生成 current_position + 5-6 条推荐   │
│        • LLM **只生成推荐理由**，affinity 数值会被后续覆盖                     │
│     c) _filter_recommendations()                                            │
│        • Layer 0: 图谱存在性校验                                             │
│        • Layer 1: 主技能门控 (必须持有该角色的核心语言/工具)                   │
│        • Layer 2: 职业信号门控 (算法岗需论文/竞赛/框架经验)                    │
│        • Layer 3: 强制包含 + job_target 置顶                                 │
│     d) locate_on_graph() 确定性排序覆盖                                      │
│        • IDF 加权技能匹配 (精确 + embedding 语义命中)                         │
│        • 标题奖励、任务匹配、能力匹配                                         │
│        • 家族先验乘性加成                                                    │
│        • rec["affinity_pct"] = int(loc_score * 100)                        │
│     e) 资历硬过滤: 0 经验 → 过滤 L4+ 岗位                                    │
│     f) 回填: LLM 返回太少时按原始技能重叠补全                                 │
│     g) 晋升目标: 有经验用户添加垂直后继节点                                   │
│     h) 丰富元数据: gap_skills, zone, salary_p50 等                          │
│     i) 缓存: Profile.cached_recs_json + CareerGoal (from_node_id)           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  8. 消费端                                                                  │
│     • GET /profiles → _profile_to_dict() → graph_position + career_goals[]  │
│     • Agent 状态 CareerState.user_profile 传入多智能体会话                   │
│     • Profile 工具: locate_on_graph, score_profile, get_user_profile        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、各模块职责边界

### 3.1 `profiles.py` — 编排层（API 入口）

**原则：薄编排，不处理业务细节**

| 端点 | 职责 |
|------|------|
| `POST /profiles/parse-resume` | 文件校验 → 文本提取 → 调用解析器 → 质量评分 → 返回预览 |
| `PUT /profiles` | 入库/合并 → 启动后台定位线程 → 返回 OK |
| `GET /profiles` | 读取 profile + goals → 序列化 → 返回完整画像 |
| `POST /profiles/reparse` | 对已有 raw_text 重新走 LLM 解析 |
| `DELETE /profiles` | 级联删除所有衍生数据 |

**注意：** `update_profile` 启动后台线程后直接返回，推荐计算是异步的。

### 3.2 `_profiles_resumesdk.py` — 商业解析器适配器

**职责：把 ResumeSDK 的原始输出映射到内部 schema**

| 函数 | 关键逻辑 |
|------|----------|
| `_call_resumesdk()` | 阿里云市场模式：JSON body + `Authorization: APPCODE {code}` |
| `_map_skills()` | 中文等级映射：精通→advanced, 熟练→intermediate, 熟悉→familiar, 了解→beginner |
| `_map_projects()` | **复杂打分去重**：ResumeSDK 常把一个大项目拆成多个管理子章节（实验论证/质量控制/迭代过程），按技术关键词密度打分，取 top 5 |
| `_map_certificates()` | 显式证书 + 正则兜底 30+ 证书类型 |
| `_supplement_skills_from_resumesdk()` | 技能 < 5 个时扫描项目/实习描述回填 |
| `_infer_primary_domain()` | 关键词推断主领域 |

**已知问题：** ResumeSDK 技能提取过粗（只返回 C++/SQL/MySQL/GitHub/Linux 等 5 个），缺少多线程/epoll 等细分技能。

### 3.3 `_profiles_parsing.py` — LLM 解析器

**职责：ResumeSDK 失败或扫描版 PDF 时的 fallback**

| 函数 | 关键逻辑 |
|------|----------|
| `_extract_profile_with_llm()` | 主入口：智能截断 → Prompt → 后处理 |
| `_smart_truncate_resume()` | 分段优先级：技能 > 项目 > 实习 > 教育 > 自我评价/爱好 |
| `_postprocess_profile()` | 奖项迁移、实习校验、技能补充 |
| `_supplement_skills_from_projects()` | 从项目描述提取 `_PROJECT_TECH_KEYWORDS` |
| `_ocr_pdf_with_vl()` | 扫描版：PDF→图片→并行 OCR |
| `_extract_profile_multimodal_vl()` | 直接用 VLM 从图片提取结构化数据（最多 3 页） |

**关键 Prompt 规则：**
- 子技能继承：C++ 是 intermediate → STL/智能指针/右值引用/移动语义至少也是 intermediate
- 等级上限从强制改为参考：有项目证据可上调
- `_SKILL_ALIASES`: ~80 条别名映射
- `_PROJECT_TECH_KEYWORDS`: ~150 条技术关键词

### 3.4 `_profiles_helpers.py` — 共享工具

| 函数 | 用途 |
|------|------|
| `_get_or_create_profile()` | 获取或创建空 Profile 行 |
| `_profile_to_dict()` | 序列化 profile + active CareerGoals |
| `_merge_profiles()` | 两个 profile dict 的并集合并 |
| `_execute_profile_reset()` | 级联删除所有衍生数据（带安全网自检） |

### 3.5 `locator.py` — 确定性图谱定位

**核心算法：IDF 加权 + 语义 embedding + 家族先验**

```
score = base * (1 + 0.35 * family_confidence)

base = skill_score * w_skill + task_score * w_task + title_score * w_title + comp_score * w_comp

有职位头衔:  skill 45% + task 10% + title 25% + competency 20%
无职位头衔(学生): skill 55% + task 20% + competency 25%
```

| 函数 | 逻辑 |
|------|------|
| `locate_on_graph()` | 主入口：返回最佳节点 + top-5 候选 + 全量分数 |
| `_infer_family_prior()` | 从简历文本推断 11 个家族的先验分布 |
| `_weighted_skill_match()` | IDF 加权 Jaccard：精确命中全额 IDF，语义命中(≥0.70) 0.7× IDF |
| `_build_skill_idf()` | 跨所有图谱节点计算技能 IDF |
| `_skill_names_from_profile()` | 聚合所有来源的技能（skills + knowledge_areas + 项目描述扫描） |

### 3.6 `_profiles_graph.py` — 推荐生成

**架构：LLM 初筛 → 确定性硬规则过滤 → locator 重排序**

| 阶段 | 函数 | 说明 |
|------|------|------|
| 预筛选 | `embedding_prefilter()` | text-embedding-v4 余弦相似度，缩小 LLM 上下文 |
| LLM 匹配 | `_llm_match_role()` | LLM 读取候选节点 → 生成推荐理由 + 当前定位 |
| 硬过滤 | `_filter_recommendations()` | 三层门控 + job_target 置顶 |
| 重排序 | `locate_on_graph()` | **覆盖 affinity_pct** 为 locator 确定性分数 |
| 资历过滤 | — | 0 经验过滤 L4+ |
| 回填 | — | 技能重叠补全 |
| 晋升 | — | 有经验用户添加垂直后继 |

**三层门控：**
- Layer 0: 节点必须存在于图谱
- Layer 1: 必须持有该角色的核心语言/工具（如 golang 岗必须会 Go）
- Layer 2: 算法/ML 岗需论文/竞赛/框架经验
- Layer 3: job_target 强制置顶（affinity  boost 到 max+5）

---

## 四、数据模型

### 4.1 Profile JSON Schema（存储于 `profile_json` 字段）

```json
{
  "name": "张三",
  "job_target": "后端开发工程师",
  "primary_domain": "backend",
  "experience_years": 2,
  "career_signals": {
    "publications": ["某论文"],
    "competitions": [],
    "open_source": [],
    "leadership": []
  },
  "education": {
    "degree": "本科",
    "school": "某某大学",
    "major": "计算机科学与技术",
    "graduation_year": 2024
  },
  "skills": [
    {"name": "C++", "level": "advanced"},
    {"name": "STL", "level": "intermediate"},
    {"name": "epoll", "level": "intermediate"}
  ],
  "knowledge_areas": ["Linux 系统编程", "高性能网络"],
  "internships": [...],
  "projects": [...],
  "awards": [...],
  "certificates": [...],
  "raw_text": "简历原始文本...",
  "preferences": {...}
}
```

### 4.2 质量评分 Schema（`quality_json`）

```json
{
  "completeness": 0.72,
  "competitiveness": 0.58,
  "dimensions": {
    "skill_coverage": 0.65,
    "skill_depth": 0.70,
    "experience": 0.40,
    "education": 0.85,
    "practice": 0.60,
    "certificates": 0.30,
    "competency": 0.55
  }
}
```

### 4.3 推荐缓存 Schema（`cached_recs_json`）

```json
{
  "hash": "profile 内容的 md5",
  "recs": [
    {
      "node_id": "golang-backend",
      "label": "Go后端开发工程师",
      "affinity_pct": 78,
      "reason": "您熟悉...",
      "zone": "主流",
      "salary_p50": 25000,
      "gap_skills": ["Go", "Gin", "gRPC"]
    }
  ]
}
```

---

## 五、已知问题与改进建议

### 5.1 当前问题

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| 1 | **ResumeSDK 技能过粗** | 只返回 5 个宽泛技能，缺少细分（如 epoll、多线程） | ResumeSDK + LLM 合并取并集 |
| 2 | **ResumeSDK 成功即不走 LLM** | LLM 能提取的细分技能被浪费 | 总是让 LLM 补充技能，与 ResumeSDK 合并 |
| 3 | **后台线程无重试** | `_auto_locate_on_graph` 用裸 `threading.Thread`，失败无感知 | 引入 Celery/RQ 或至少加重试装饰器 |
| 4 | **OCR 截断** | 扫描版 > 5 页丢弃尾部 | 分页分批 OCR，或改用支持长文档的模型 |
| 5 | **LLM Prompt 过大** | `_RESUME_PARSE_PROMPT` ~120 行，维护困难 | 拆分为系统提示 + 字段规则 JSON |
| 6 | **技能别名硬编码** | `_SKILL_ALIASES` + `_PROJECT_TECH_KEYWORDS` ~230 条 | 考虑从 JD 数据自动构建 |
| 7 | **实习误分类** | 两端解析器都有复杂启发式区分实习/项目 | 用 LLM 做后处理分类，替代规则 |
| 8 | **GET 时执行 lazy migration** | `_lazy_fix_misclassified_internships` 每次 GET 都跑 | 改为一次性迁移脚本 |
| 9 | **Graph cache 竞态** | `mtime` 检测可能 race | 加文件锁或改用显式版本号 |

### 5.2 架构改进方向

```
当前:  profiles.py 直接调用 _profiles_resumesdk.py / _profiles_parsing.py
       → 解析逻辑与 API 层耦合

建议:  引入 ProfileParser 抽象层

       backend/services/profile/
       ├── parser/
       │   ├── __init__.py
       │   ├── base.py          # ProfileParser 抽象基类
       │   ├── resumesdk.py     # ResumeSDKParser
       │   ├── llm.py           # LLMParser
       │   ├── ocr.py           # OCRPipeline
       │   └── merger.py        # 多解析器结果合并
       ├── extractor/           # 字段提取器（技能、证书、项目等）
       │   ├── skill.py
       │   ├── certificate.py
       │   └── project.py
       └── postprocessor/       # 后处理（归一化、补充、校验）
           ├── normalizer.py
           ├── supplement.py
           └── validator.py
```

### 5.3 解析器合并方案（ResumeSDK + LLM）

```python
# 建议的合并策略
async def parse_resume(content, filename, raw_text):
    results = await asyncio.gather(
        parse_with_resumesdk(content, filename),
        parse_with_llm(raw_text),
        return_exceptions=True
    )
    
    sdk_profile = results[0] if not isinstance(results[0], Exception) else None
    llm_profile = results[1] if not isinstance(results[1], Exception) else None
    
    if sdk_profile and llm_profile:
        # 合并取并集：ResumeSDK 提供基础字段，LLM 补充细分技能
        merged = merge_parsed_profiles(sdk_profile, llm_profile)
        # 技能合并策略：并集，LLM 的细分技能优先，ResumeSDK 的等级优先
        return merged
    elif sdk_profile:
        return sdk_profile
    elif llm_profile:
        return llm_profile
    else:
        raise ParseError("All parsers failed")
```

---

## 六、关键常量速查

| 常量 | 位置 | 说明 |
|------|------|------|
| `_MAX_SIZE = 10MB` | `profiles.py` | 文件大小上限 |
| `_ALLOWED_EXTENSIONS` | `profiles.py` | `.pdf`, `.doc`, `.docx`, `.txt` |
| `_SKILL_ALIASES` | `_profiles_parsing.py` | ~80 条技能别名 |
| `_PROJECT_TECH_KEYWORDS` | `_profiles_parsing.py` | ~150 条技术关键词 |
| `_CERTIFICATE_PATTERNS` | `_profiles_parsing.py` | 30+ 证书正则 |
| `_LEVEL_ORDER` | `_profiles_helpers.py` | beginner < familiar < intermediate < advanced |
| `FAMILY_KEYWORDS` | `shared.py` | 11 个职业家族关键词 |
| `_ROLE_PRIMARY_REQUIREMENTS` | `_profiles_graph.py` | 14 个角色的主技能门控 |
| `_ROLE_SIGNAL_REQUIREMENTS` | `_profiles_graph.py` | 3 个研究岗的职业信号门控 |

---

## 七、调试指南

### 7.1 查看解析日志

```bash
# 查找最近的解析请求
grep -n "parse_resume\|Resume parser strategy" backend/logs/app.log | tail -20

# 查看 ResumeSDK 调用详情
grep -n "resumesdk\|ResumeSDK" backend/logs/app.log | tail -20

# 查看定位结果
grep -n "locate_on_graph\|_auto_locate" backend/logs/app.log | tail -20
```

### 7.2 手动触发重解析

```bash
curl -X POST http://localhost:8000/profiles/reparse \
  -H "Authorization: Bearer $TOKEN"
```

### 7.3 检查缓存

```python
# 在 Python 控制台中
from backend.services.profile.locator import locate_on_graph
from backend.services.graph_service import GraphService

graph = GraphService()
profile = {...}  # 你的测试画像
result = locate_on_graph(profile, graph)
print(result["node_id"], result["score"])
for c in result["candidates"]:
    print(f"  {c['node_id']}: {c['score']:.3f}")
```
