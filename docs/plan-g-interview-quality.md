# 模拟面试出题质量优化方案

> 状态：待实现  
> 问题来源：2026-04-06 用户反馈"面试题目质量低、与岗位不符合，没有结合岗位出题"  
> 涉及文件：`backend/interview.py` · `backend/services/mock_service.py`

---

## 一、完整链路问题诊断

### 问题 1【P0】：JD 文本截断到 500 字（`mock_service.py:223`）

```python
"jd_text": jd.jd_text[:500],   # 绑定瓶颈
```
完整 JD 通常 1500-3000 字。500 字后核心技术栈、职责细节、加分项全部丢失。LLM 出题时看不到岗位真实要求。

**修复：** 改为 `jd.jd_text[:2500]`，同步修改 `interview.py` 里的 `[:1000]` 为 `[:2500]`。

---

### 问题 2【P0】：面试官 chat 上下文里完全没有 JD 信息（`mock_service.py:303`）

`_CONTEXT_TEMPLATE` 传给面试官的内容只有：
- 岗位名称（如"前端工程师"）
- 题目列表（仅题号+题目文字）
- 候选人技能名称列表

**没有 JD 原文、没有缺口技能、没有候选人弱项**。面试官追问（0-1次）完全随机，不针对岗位要求和候选人薄弱点。

**修复：** `_CONTEXT_TEMPLATE` 增加以下字段：
```
【岗位核心要求（JD摘要）】
{jd_summary}

【候选人主要技能缺口】
{gap_skills_summary}
```
`start_session()` 保存 `jd_summary`（JD 前 800 字）和 `gap_skills_summary` 到 session 对象。

---

### 问题 3【P0】：传给面试官的题目缺少 `focus_skill` 和 `answer_key`（`mock_service.py:299`）

当前传入：
```python
f"第{q['round']}题 [{q.get('type', '')}]: {q['question']}"
```
缺失：
- `focus_skill`：面试官不知道这题考察什么，追问方向随机
- `answer_key`：面试官不知道标准答案要点，无法判断回答是否到位

**修复：** 改为：
```python
f"第{q['round']}题 [{q.get('type','')}]（考点: {q.get('focus_skill','')}）: {q['question']}"
+ (f"\n  参考要点: {q['answer_key']}" if q.get('answer_key') else "")
```

---

### 问题 4【P0】：面试官 Prompt 没有追问策略（`_BASE_INTERVIEWER`）

当前 prompt 只规定行为规范（几题、用中性语言、格式），**没有告诉面试官：**
- 候选人哪些技能是弱项，应重点追问
- 追问时应验证什么（是否真的掌握，还是只会背概念）
- 对于项目经验题，应追问具体细节（不是泛泛而谈）

**修复：** 在 prompt 中增加追问策略：
```
追问策略：
- 候选人回答含糊或只给结论时，追问"能说说具体是怎么实现的吗？"
- 对候选人的技能缺口项，用引导式提问探测真实水平：先问基础，再问应用
- 对项目经验题，追问技术决策原因（"为什么选这个方案而不是XXX？"）
- 不接受"我了解这个"式的空话，需要候选人给出具体例子
```

---

### 问题 5【P1】：session 里 profile_summary 只有技能名列表（`mock_service.py:207`）

```python
profile_summary = f"技能: {'、'.join(names)}"
```
项目描述、工作经验、技术细节全部丢失。面试官和出题时都用这个摘要，导致"项目经验题"出不了针对性的题，追问也无从下手。

**修复：** 扩充 profile_summary 构建：
```python
parts = []
if skills:
    parts.append(f"技能: {'、'.join(names[:10])}")
projects = profile_data.get("projects", [])
for p in projects[:3]:
    name = p.get("name", "")
    tech = p.get("tech_stack", "") or p.get("technologies", "")
    desc = p.get("description", "") or p.get("highlights", "")
    if name:
        line = f"项目《{name}》"
        if tech: line += f"（{str(tech)[:60]}）"
        if desc: line += f": {str(desc)[:80]}"
        parts.append(line)
profile_summary = "\n".join(parts) if parts else "暂无"
```

---

### 问题 6【P1】：出题时 `gap_skills` 的 gap_level 被丢弃（`interview.py:85`）

```python
missing_names.append(m.get("skill", str(m)))  # 只取名字
```
JD 诊断返回的 `gap_skills` 结构是 `{skill, gap_level: major/minor, suggestion}`。
`gap_level` 直接决定出题难度：major 缺口应出引导式简单题，minor 缺口出 medium 题。

**修复：** 保留 gap_level：
```python
level_map = {"major": "严重缺失", "minor": "有差距", "nice_to_have": "加分项"}
line = m.get("skill", "")
if m.get("gap_level"):
    line += f"（{level_map.get(m['gap_level'], '')}）"
missing_parts.append(line)
```

---

### 问题 7【P1】：question_bank 题目与 JD 完全无关（`mock_service.py:239`）

无 JD 模式优先从 question_bank 随机抽题。题库题目是通用技术题，与具体岗位要求无任何关联。用户选了 JD 做面试，却因为走了 question_bank 分支拿到通用题。

**修复：** 调整选题逻辑：
```python
if skill_tags:
    # 用户明确选了题库范围 → question_bank
    questions = _sample_from_question_bank(db, skill_tags=skill_tags, count=5)
elif jd_id:
    # 有 JD → 必须 LLM 生成，不走 question_bank
    questions = await generate_questions_async(jd_context, profile_data, count=5)
else:
    # 无 JD 无 tags → LLM 生成通用题（比随机抽题质量更高）
    questions = await generate_questions_async(jd_context, profile_data, count=5)
```

---

### 问题 8【P1】：出题模型用 qwen3.5-flash，推理能力不足（`interview.py:122`）

```python
model = os.getenv("CHAT_LLM_MODEL") or os.getenv("LLM_MODEL") or "qwen3.5-flash"
```
出题是高推理任务（从长文本 JD 提炼考点 + 结合画像设计梯度题），flash 模型能力不够，产出平庸。

**修复：** 出题单独配置：
```python
model = os.getenv("INTERVIEW_GEN_MODEL") or os.getenv("LLM_MODEL") or "qwen-plus"
```

---

### 问题 9【P2】：出题 Prompt 缺少强制约束（`interview.py:_QUESTION_GEN_USER`）

当前 prompt 没有硬性要求题目必须来自 JD，LLM 倾向于出通用八股题。

**修复：** 增加强制约束段：
```
【强制要求 — 违反则重新生成】
1. 至少 3 道题的考察点必须来自 JD 文本中明确出现的技术/框架/工具名称
2. 禁止出通用计算机基础题（链表、排序、操作系统原理等），除非 JD 明确提到算法
3. 项目经验题必须基于候选人档案中列出的真实项目，不可虚构项目名
4. 薄弱探测题：major 缺口出 easy 引导题，minor 缺口出 medium 题
```

---

## 二、实现顺序

```
Step 1: mock_service.py — 扩大 jd_text 到 2500 字（2行）
Step 2: mock_service.py — 扩充 profile_summary（项目描述）
Step 3: mock_service.py — context_template 加入 jd_summary + gap_skills
Step 4: mock_service.py — 题目传给面试官时加 focus_skill + answer_key
Step 5: mock_service.py — 修复 question_bank 绕过 JD 的逻辑
Step 6: interview.py   — gap_level 保留到 missing_str
Step 7: interview.py   — 出题 Prompt 增加强制约束
Step 8: interview.py   — 出题模型改 qwen-plus，新增 INTERVIEW_GEN_MODEL 环境变量
Step 9: mock_service.py — _BASE_INTERVIEWER 增加追问策略
```

---

## 三、预期效果

| 改动 | 当前 | 改后 |
|------|------|------|
| JD 文本 | 500 字，核心要求被截 | 2500 字，完整技术栈可见 |
| 出题依据 | 只有岗位名称 | JD 全文 + 候选人缺口 + 项目详情 |
| 面试官追问 | 随机 | 针对缺口技能 + 项目技术决策 |
| 面试官上下文 | 无 JD，无弱项 | JD 摘要 + gap 缺口 |
| 出题模型 | qwen3.5-flash | qwen-plus |
| question_bank 使用场景 | 有 JD 时也可能走到 | 仅用于用户手动选题库场景 |

---

## 四、关联文件

| 文件 | 主要改动 |
|------|----------|
| `backend/services/mock_service.py` | jd_text 截断、profile_summary、_CONTEXT_TEMPLATE、题目格式、选题逻辑、_BASE_INTERVIEWER |
| `backend/interview.py` | gap_level 保留、出题 Prompt 约束、模型配置 |
| `.env.example` | 新增 `INTERVIEW_GEN_MODEL` |
