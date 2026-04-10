# Soft Skills Assessment Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 5-dimension static SJT + LLM fusion scoring with a 3-dimension template-based LLM-personalized SJT that displays levels instead of scores and provides actionable advice.

**Architecture:** Backend adds a `/sjt/generate` endpoint that fills 15 scenario templates via LLM, stores the session in a new `SjtSession` table, then scores submissions and generates advice via a second LLM call. Frontend replaces the static question flow with a generate → answer → result flow showing 4-level badges instead of numeric scores.

**Tech Stack:** Python/FastAPI, SQLAlchemy (SQLite), OpenAI-compatible LLM (DashScope), React/TypeScript, Tailwind CSS, framer-motion

**Spec:** `docs/superpowers/specs/2026-04-04-soft-skills-redesign.md`

---

### Task 1: Create SJT scenario templates (`data/sjt_templates.json`)

**Files:**
- Create: `data/sjt_templates.json`
- Delete: `data/sjt_questions.json` (after Task 5 removes references)

- [ ] **Step 1: Create the 15 templates file**

Write `data/sjt_templates.json` with 15 templates (5 per dimension). Each template has `scenario_template` with `{slot}` placeholders, 4 options with fixed efficacy (1-4), and `fill_slots` listing the slot names.

```json
{
  "version": 2,
  "dimensions": ["communication", "learning", "collaboration"],
  "templates": [
    {
      "id": "t01",
      "dimension": "communication",
      "scenario_template": "你负责向{stakeholder}汇报{project_type}项目的进展，但对方对技术细节不感兴趣，只关心{business_concern}。汇报前一天你发现了一个{risk_type}风险。你会怎么做？",
      "fill_slots": ["stakeholder", "project_type", "business_concern", "risk_type"],
      "options": [
        {"id": "a", "text_template": "直接用技术语言详细说明{risk_type}的影响和原因", "efficacy": 2},
        {"id": "b", "text_template": "用{stakeholder}关心的{business_concern}角度重新包装风险信息，同时附上应对方案", "efficacy": 4},
        {"id": "c", "text_template": "先不提风险，等内部解决了再汇报", "efficacy": 1},
        {"id": "d", "text_template": "简要提及风险存在，但把重点放在已取得的进展上", "efficacy": 3}
      ]
    },
    {
      "id": "t02",
      "dimension": "communication",
      "scenario_template": "在{team_context}的一次需求评审会上，{role_a}和{role_b}对{feature}的实现方式产生了分歧，讨论逐渐升温。作为参会者，你会怎么做？",
      "fill_slots": ["team_context", "role_a", "role_b", "feature"],
      "options": [
        {"id": "a", "text_template": "保持沉默，等他们自己解决", "efficacy": 1},
        {"id": "b", "text_template": "先分别复述双方的核心诉求，确认理解无误后再引导讨论折中方案", "efficacy": 4},
        {"id": "c", "text_template": "直接站队支持你认为技术上更合理的一方", "efficacy": 2},
        {"id": "d", "text_template": "建议先搁置争议，会后各自准备方案再对比", "efficacy": 3}
      ]
    },
    {
      "id": "t03",
      "dimension": "communication",
      "scenario_template": "你刚加入{team_name}团队，负责{task_area}模块。联调时发现上游{upstream_team}提供的接口文档和实际行为不一致，影响了你的开发进度。你会怎么做？",
      "fill_slots": ["team_name", "task_area", "upstream_team"],
      "options": [
        {"id": "a", "text_template": "自己看源码猜测正确行为，先绕过去", "efficacy": 2},
        {"id": "b", "text_template": "整理出具体的不一致点，附上请求和响应截图，通过工作群 @ 对方确认", "efficacy": 4},
        {"id": "c", "text_template": "直接在群里说'你们文档是错的'，让对方更新", "efficacy": 1},
        {"id": "d", "text_template": "先和自己的 leader 反馈，让 leader 去协调", "efficacy": 3}
      ]
    },
    {
      "id": "t04",
      "dimension": "communication",
      "scenario_template": "你在做{project_name}项目的技术方案分享，台下有技术同事也有{non_tech_audience}。{non_tech_audience}中有人提问：'{question}'。你会怎么回应？",
      "fill_slots": ["project_name", "non_tech_audience", "question"],
      "options": [
        {"id": "a", "text_template": "用专业术语详细解释技术原理", "efficacy": 1},
        {"id": "b", "text_template": "用类比和业务场景来回答，确保{non_tech_audience}也能理解", "efficacy": 4},
        {"id": "c", "text_template": "说'这个问题比较技术，我们会后单独聊'", "efficacy": 2},
        {"id": "d", "text_template": "简要回答后反问对方最关心的是哪个方面，再针对性展开", "efficacy": 3}
      ]
    },
    {
      "id": "t05",
      "dimension": "communication",
      "scenario_template": "你的{deliverable}被{reviewer}评审后收到了大量修改意见，其中有几条你认为不合理或基于对需求的误解。你会怎么处理？",
      "fill_slots": ["deliverable", "reviewer"],
      "options": [
        {"id": "a", "text_template": "全部接受修改，避免冲突", "efficacy": 2},
        {"id": "b", "text_template": "逐条回复：认同的说明修改计划，不认同的附上你的理解和依据，约一次面对面沟通", "efficacy": 4},
        {"id": "c", "text_template": "在群里逐条反驳不合理的意见", "efficacy": 1},
        {"id": "d", "text_template": "只改你认同的部分，不合理的默默忽略", "efficacy": 1}
      ]
    },
    {
      "id": "t06",
      "dimension": "learning",
      "scenario_template": "团队决定在{project_context}中引入{new_tech}，你之前没接触过这项技术，但需要在{timeline}内用它完成{task}。你会怎么做？",
      "fill_slots": ["project_context", "new_tech", "timeline", "task"],
      "options": [
        {"id": "a", "text_template": "从官方文档和教程开始，边学边写一个最小可用原型验证关键功能", "efficacy": 4},
        {"id": "b", "text_template": "找一个完整的课程系统学习，确保基础扎实后再动手", "efficacy": 2},
        {"id": "c", "text_template": "直接从 StackOverflow 和 AI 助手复制代码拼凑，能跑就行", "efficacy": 1},
        {"id": "d", "text_template": "先问团队里有经验的人推荐学习路径，然后快速过一遍核心概念再开始", "efficacy": 3}
      ]
    },
    {
      "id": "t07",
      "dimension": "learning",
      "scenario_template": "你在{current_domain}工作了一段时间后，被调到了一个完全陌生的{new_domain}项目组。项目已经进行到中期，团队在讨论{topic}时你很多概念听不懂。你会怎么做？",
      "fill_slots": ["current_domain", "new_domain", "topic"],
      "options": [
        {"id": "a", "text_template": "假装听懂了，回去自己百度", "efficacy": 1},
        {"id": "b", "text_template": "会后整理不懂的关键词，阅读项目文档和 wiki，再约一位同事请教确认理解", "efficacy": 4},
        {"id": "c", "text_template": "当场就每个不懂的词提问，打断讨论节奏", "efficacy": 2},
        {"id": "d", "text_template": "把不懂的术语记下来，等项目结束后再慢慢学", "efficacy": 1}
      ]
    },
    {
      "id": "t08",
      "dimension": "learning",
      "scenario_template": "你在{project}中使用的{technology}发布了一个大版本更新，引入了{breaking_change}。团队还没有升级计划，但你注意到新版本解决了你当前遇到的{pain_point}。你会怎么做？",
      "fill_slots": ["project", "technology", "breaking_change", "pain_point"],
      "options": [
        {"id": "a", "text_template": "等团队统一安排升级", "efficacy": 2},
        {"id": "b", "text_template": "在个人分支上做一次升级验证，记录影响范围和改动量，写成简短评估发给团队参考", "efficacy": 4},
        {"id": "c", "text_template": "直接在主分支升级，出了问题再回滚", "efficacy": 1},
        {"id": "d", "text_template": "阅读 changelog 了解变更，评估是否值得升级，但不主动推动", "efficacy": 3}
      ]
    },
    {
      "id": "t09",
      "dimension": "learning",
      "scenario_template": "你做完{task}的代码提交后，code review 中收到了一条你不理解的建议：'{review_comment}'。这个建议来自{senior_role}。你会怎么做？",
      "fill_slots": ["task", "review_comment", "senior_role"],
      "options": [
        {"id": "a", "text_template": "直接按建议改了，毕竟是{senior_role}说的", "efficacy": 2},
        {"id": "b", "text_template": "先查资料理解建议背后的原理，再在 review 中回复你的理解，确认理解是否正确后再改", "efficacy": 4},
        {"id": "c", "text_template": "回复'不理解为什么要这么改'，等对方解释", "efficacy": 3},
        {"id": "d", "text_template": "忽略这条建议，你觉得现在的写法也没问题", "efficacy": 1}
      ]
    },
    {
      "id": "t10",
      "dimension": "learning",
      "scenario_template": "你发现自己在{skill_area}方面的知识明显落后于团队平均水平，这影响了你在{work_context}中的效率。但手头的{current_task}又很紧急。你会怎么做？",
      "fill_slots": ["skill_area", "work_context", "current_task"],
      "options": [
        {"id": "a", "text_template": "先赶{current_task}，以后再说", "efficacy": 1},
        {"id": "b", "text_template": "每天抽 30-60 分钟针对性学习{skill_area}的核心内容，同时在{current_task}中刻意练习", "efficacy": 4},
        {"id": "c", "text_template": "请 leader 把{skill_area}相关的任务暂时分给别人", "efficacy": 1},
        {"id": "d", "text_template": "找团队里擅长{skill_area}的同事结对，边做边学", "efficacy": 3}
      ]
    },
    {
      "id": "t11",
      "dimension": "collaboration",
      "scenario_template": "你和{colleague}共同负责{project}的开发，但你们在{decision_point}上有不同意见。{colleague}坚持用方案 A，你认为方案 B 更合理。deadline 快到了。你会怎么做？",
      "fill_slots": ["colleague", "project", "decision_point"],
      "options": [
        {"id": "a", "text_template": "坚持己见，拉更多人支持你的方案", "efficacy": 2},
        {"id": "b", "text_template": "约{colleague}对齐，各自列出方案的优劣，一起定一个评估标准来决策", "efficacy": 4},
        {"id": "c", "text_template": "让步用方案 A，反正时间来不及了", "efficacy": 2},
        {"id": "d", "text_template": "找 leader 来裁决", "efficacy": 1}
      ]
    },
    {
      "id": "t12",
      "dimension": "collaboration",
      "scenario_template": "在{project}中，{teammate}负责的{module}模块进度严重滞后，已经开始影响你负责的{your_module}。{teammate}看起来压力很大但没有主动求助。你会怎么做？",
      "fill_slots": ["project", "teammate", "module", "your_module"],
      "options": [
        {"id": "a", "text_template": "在站会上公开指出{teammate}的进度问题", "efficacy": 1},
        {"id": "b", "text_template": "私下找{teammate}聊，了解困难所在，看自己能否分担一部分或帮忙解决卡点", "efficacy": 4},
        {"id": "c", "text_template": "向 leader 反馈进度风险，让 leader 决定如何调配", "efficacy": 3},
        {"id": "d", "text_template": "先把自己的部分做好，用 mock 数据绕过依赖", "efficacy": 2}
      ]
    },
    {
      "id": "t13",
      "dimension": "collaboration",
      "scenario_template": "你被临时拉进一个跨团队协作项目，负责{your_part}。{other_team}团队的工作方式和你们团队差异很大——他们习惯{their_style}，而你们团队习惯{your_style}。你会怎么做？",
      "fill_slots": ["your_part", "other_team", "their_style", "your_style"],
      "options": [
        {"id": "a", "text_template": "坚持用你们团队的方式，毕竟你更熟悉", "efficacy": 1},
        {"id": "b", "text_template": "先了解对方工作方式的原因和优势，在关键协作节点约定统一规范，其他部分各自灵活处理", "efficacy": 4},
        {"id": "c", "text_template": "完全按对方的方式来，减少摩擦", "efficacy": 2},
        {"id": "d", "text_template": "提议双方在项目开始时开个对齐会，商定协作流程", "efficacy": 3}
      ]
    },
    {
      "id": "t14",
      "dimension": "collaboration",
      "scenario_template": "在{project}的冲刺阶段，你完成了自己的{your_task}，但团队中{struggling_member}还在处理{their_task}，整体交付有风险。你会怎么做？",
      "fill_slots": ["project", "your_task", "struggling_member", "their_task"],
      "options": [
        {"id": "a", "text_template": "你的活干完了，等着就好", "efficacy": 1},
        {"id": "b", "text_template": "主动了解{their_task}的卡点，看能否帮忙拆解或接手其中一部分，确保团队整体交付", "efficacy": 4},
        {"id": "c", "text_template": "帮忙做测试或写文档等周边工作，减轻{struggling_member}的负担", "efficacy": 3},
        {"id": "d", "text_template": "提醒 leader 关注这个风险", "efficacy": 2}
      ]
    },
    {
      "id": "t15",
      "dimension": "collaboration",
      "scenario_template": "你所在的团队刚完成{project}的交付，准备复盘。有人提出{controversial_opinion}，团队气氛变得有些紧张。你会怎么做？",
      "fill_slots": ["project", "controversial_opinion"],
      "options": [
        {"id": "a", "text_template": "转移话题，避免气氛更尴尬", "efficacy": 1},
        {"id": "b", "text_template": "认可这个观点值得讨论，引导大家聚焦在'下次怎么改进'而不是'谁的责任'", "efficacy": 4},
        {"id": "c", "text_template": "附和这个观点，确实应该正视问题", "efficacy": 2},
        {"id": "d", "text_template": "建议用匿名方式收集复盘意见，减少面对面的对抗感", "efficacy": 3}
      ]
    }
  ]
}
```

- [ ] **Step 2: Validate template structure**

Run a quick sanity check:

```bash
python -c "
import json
data = json.loads(open('data/sjt_templates.json', encoding='utf-8').read())
assert data['version'] == 2
assert len(data['templates']) == 15
dims = {}
for t in data['templates']:
    dims.setdefault(t['dimension'], []).append(t['id'])
    effs = sorted(o['efficacy'] for o in t['options'])
    assert len(t['options']) == 4, f'{t[\"id\"]}: need 4 options'
    assert effs[0] >= 1 and effs[-1] <= 4, f'{t[\"id\"]}: efficacy out of range'
    assert len(t['fill_slots']) > 0, f'{t[\"id\"]}: no fill_slots'
for d in ['communication', 'learning', 'collaboration']:
    assert len(dims[d]) == 5, f'{d}: expected 5, got {len(dims[d])}'
print('OK: 15 templates, 3 dimensions x 5 each, all efficacy values valid')
"
```

Expected: `OK: 15 templates, 3 dimensions x 5 each, all efficacy values valid`

- [ ] **Step 3: Commit**

```bash
git add data/sjt_templates.json
git commit -m "feat(sjt): add 15 scenario templates for v2 soft skills assessment"
```

---

### Task 2: Add `SjtSession` database model

**Files:**
- Modify: `backend/db_models.py` (add SjtSession class after Profile, ~line 86)

- [ ] **Step 1: Add SjtSession model to db_models.py**

Add after the `Profile` class (after line 86 in `backend/db_models.py`):

```python
class SjtSession(Base):
    """Temporary storage for generated SJT questions between generate and submit."""
    __tablename__ = "sjt_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id"), nullable=False, index=True
    )
    questions_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

- [ ] **Step 2: Verify the app starts and table is created**

```bash
python -c "
from backend.db import engine
from backend.db_models import Base, SjtSession
Base.metadata.create_all(engine)
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
assert 'sjt_sessions' in tables, f'sjt_sessions not found in {tables}'
cols = [c['name'] for c in inspector.get_columns('sjt_sessions')]
assert set(cols) >= {'id', 'profile_id', 'questions_json', 'created_at', 'expires_at'}
print('OK: sjt_sessions table created with correct columns')
"
```

Expected: `OK: sjt_sessions table created with correct columns`

- [ ] **Step 3: Commit**

```bash
git add backend/db_models.py
git commit -m "feat(db): add SjtSession table for temporary SJT question storage"
```

---

### Task 3: Backend — SJT generate endpoint

**Files:**
- Modify: `backend/routers/profiles.py` (replace `GET /sjt/questions` with `POST /sjt/generate`)
- Modify: `backend/services/profile_service.py` (add `generate_sjt_questions` method, update `_load_sjt_questions` → `_load_sjt_templates`)

- [ ] **Step 1: Add template loading and LLM slot-filling to `profile_service.py`**

Replace `_load_sjt_questions` (lines 1481-1486) and add the new method. In `backend/services/profile_service.py`:

Replace:
```python
    @staticmethod
    def _load_sjt_questions() -> list[dict]:
        """Load SJT question bank from data/sjt_questions.json."""
        path = _PROJECT_ROOT / "data" / "sjt_questions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["questions"]
```

With:
```python
    @staticmethod
    def _load_sjt_templates() -> list[dict]:
        """Load SJT scenario templates from data/sjt_templates.json."""
        path = _PROJECT_ROOT / "data" / "sjt_templates.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["templates"]

    @staticmethod
    def generate_sjt_questions(profile_data: dict) -> list[dict]:
        """Fill SJT templates with personalized context based on user's resume.

        Returns list of questions with filled scenarios/options AND efficacy values
        (caller must strip efficacy before sending to client).
        """
        from backend.llm import llm_chat, parse_json_response, get_model

        templates = ProfileService._load_sjt_templates()

        # Build resume summary for LLM context
        skills = [s.get("name", "") for s in profile_data.get("skills", [])[:10]]
        projects = profile_data.get("projects", [])[:3]
        education = profile_data.get("education", {})
        experience_years = profile_data.get("experience_years", 0)

        resume_summary = (
            f"技能: {', '.join(skills)}\n"
            f"项目经验: {'; '.join(p if isinstance(p, str) else p.get('description', str(p)) for p in projects)}\n"
            f"教育: {education.get('degree', '')} {education.get('major', '')} {education.get('school', '')}\n"
            f"工作年限: {experience_years}"
        )

        # Build slot fill request
        slot_request = []
        for t in templates:
            slot_request.append({
                "id": t["id"],
                "dimension": t["dimension"],
                "fill_slots": t["fill_slots"],
                "scenario_hint": t["scenario_template"][:60] + "...",
            })

        prompt = f"""你是一个 SJT（情境判断测验）情境个性化助手。

用户简历摘要：
{resume_summary}

请根据用户的行业背景和经历，为以下 15 道情境题的占位符填充具体内容。
填充要求：
- 内容必须贴合用户的行业/技术栈/项目经验
- 每个 slot 填 2-8 个字的短语
- 不要改变题目结构，只填空

请返回严格 JSON，格式为：
{{
  "fills": [
    {{"id": "t01", "slots": {{"stakeholder": "产品总监", "project_type": "电商推荐系统", ...}}}},
    ...
  ]
}}

需要填充的模板：
{json.dumps(slot_request, ensure_ascii=False, indent=2)}

只返回 JSON，不要有任何其他文字。"""

        result = llm_chat(
            [{"role": "user", "content": prompt}],
            model=get_model("default"),
            temperature=0.7,
            timeout=30,
        )
        fills_data = parse_json_response(result)
        fills_map = {f["id"]: f.get("slots", {}) for f in fills_data.get("fills", [])}
        if not fills_map:
            raise ValueError("LLM returned empty fills")

        # Apply fills to templates
        questions = []
        for t in templates:
            slots = fills_map.get(t["id"], {})
            # Fill scenario
            scenario = t["scenario_template"]
            for slot_name, slot_value in slots.items():
                scenario = scenario.replace("{" + slot_name + "}", str(slot_value))
            # Fill options
            options = []
            for o in t["options"]:
                text = o.get("text_template", o.get("text", ""))
                for slot_name, slot_value in slots.items():
                    text = text.replace("{" + slot_name + "}", str(slot_value))
                options.append({
                    "id": o["id"],
                    "text": text,
                    "efficacy": o["efficacy"],
                })
            questions.append({
                "id": t["id"],
                "dimension": t["dimension"],
                "scenario": scenario,
                "options": options,
            })

        return questions
```

- [ ] **Step 2: Replace GET `/sjt/questions` with POST `/sjt/generate` in `profiles.py` router**

In `backend/routers/profiles.py`, replace lines 416-432 (the `GET /sjt/questions` endpoint and section comment):

Replace:
```python
# ── SJT soft-skill assessment ───────────────────────────────────────────────

@router.get("/sjt/questions")
def get_sjt_questions(user: User = Depends(get_current_user)):
    """Return the SJT question bank."""
    from backend.services.profile_service import ProfileService
    questions = ProfileService._load_sjt_questions()
    # Strip efficacy values so client can't cheat
    safe = []
    for q in questions:
        safe.append({
            "id": q["id"],
            "dimension": q["dimension"],
            "scenario": q["scenario"],
            "options": [{"id": o["id"], "text": o["text"]} for o in q["options"]],
        })
    return safe
```

With:
```python
# ── SJT soft-skill assessment (v2: template-based, LLM-personalized) ──────

class SjtGenerateRequest(BaseModel):
    profile_id: int


@router.post("/sjt/generate")
def generate_sjt(
    req: SjtGenerateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate personalized SJT questions based on user's profile."""
    import uuid
    from datetime import datetime, timedelta, timezone
    from backend.db_models import SjtSession
    from backend.services.profile_service import ProfileService

    profile = (
        db.query(Profile)
        .filter(Profile.id == req.profile_id, Profile.user_id == user.id)
        .first()
    )
    if not profile:
        raise HTTPException(404, "画像不存在")

    profile_data = json.loads(profile.profile_json or "{}")

    # Generate personalized questions (includes efficacy); retry once on failure
    try:
        questions = ProfileService.generate_sjt_questions(profile_data)
    except Exception:
        try:
            questions = ProfileService.generate_sjt_questions(profile_data)
        except Exception as e:
            raise HTTPException(500, f"生成失败，请重试: {e}")

    # Store session with efficacy for later scoring
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    session = SjtSession(
        id=session_id,
        profile_id=profile.id,
        questions_json=json.dumps(questions, ensure_ascii=False),
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    db.add(session)
    db.commit()

    # Strip efficacy before returning to client
    safe_questions = []
    for q in questions:
        safe_questions.append({
            "id": q["id"],
            "dimension": q["dimension"],
            "scenario": q["scenario"],
            "options": [{"id": o["id"], "text": o["text"]} for o in q["options"]],
        })

    return ok({"session_id": session_id, "questions": safe_questions})
```

- [ ] **Step 3: Verify generate endpoint imports and server starts**

```bash
python -c "
from backend.app import create_app
app = create_app()
routes = [r.path for r in app.routes if hasattr(r, 'path')]
assert '/api/profiles/sjt/generate' in routes or any('sjt/generate' in r for r in routes), f'Route not found in {routes}'
print('OK: /sjt/generate route registered')
"
```

- [ ] **Step 4: Commit**

```bash
git add backend/services/profile_service.py backend/routers/profiles.py
git commit -m "feat(sjt): add POST /sjt/generate endpoint with LLM template filling"
```

---

### Task 4: Backend — Redesign SJT submit endpoint

**Files:**
- Modify: `backend/routers/profiles.py` (rewrite `POST /sjt/submit`)
- Modify: `backend/services/profile_service.py` (rewrite `score_sjt`, delete `fuse_with_llm`, add `generate_sjt_advice`)

- [ ] **Step 1: Rewrite `score_sjt` and delete `fuse_with_llm` in `profile_service.py`**

Replace `score_sjt` (lines 1488-1522) and `fuse_with_llm` (lines 1524-1540) with:

```python
    _LEVEL_MAP = [
        (80, "优秀"),
        (60, "良好"),
        (40, "基础"),
        (0, "待发展"),
    ]

    @staticmethod
    def score_to_level(score: float) -> str:
        """Map 0-100 score to 4-tier level."""
        for threshold, level in ProfileService._LEVEL_MAP:
            if score >= threshold:
                return level
        return "待发展"

    @staticmethod
    def score_sjt_v2(answers: list[dict], questions: list[dict]) -> dict:
        """Score SJT v2 answers using session questions (with efficacy).

        Args:
            answers: [{"question_id": "t01", "best": "b", "worst": "c"}, ...]
            questions: Full question list from SjtSession (with efficacy)

        Returns:
            {"dimensions": {"communication": {"score": 72, "level": "良好"}, ...}}
        """
        q_map = {q["id"]: q for q in questions}
        dim_scores: dict[str, list[float]] = {}

        for ans in answers:
            q = q_map.get(ans.get("question_id", ""))
            if not q:
                continue
            options = {o["id"]: o["efficacy"] for o in q["options"]}
            best_eff = options.get(ans.get("best", ""), 2)
            worst_eff = options.get(ans.get("worst", ""), 3)
            raw = best_eff + (4 - worst_eff)
            # Corrected normalization: actual range is 2-7
            normalized = max(0, min(100, round((raw - 2) / 5 * 100)))
            dim_scores.setdefault(q["dimension"], []).append(normalized)

        dimensions = {}
        for dim, vals in dim_scores.items():
            avg = round(sum(vals) / len(vals))
            dimensions[dim] = {
                "score": avg,
                "level": ProfileService.score_to_level(avg),
            }

        return {"dimensions": dimensions}

    @staticmethod
    def generate_sjt_advice(
        dimensions: dict,
        answers: list[dict],
        questions: list[dict],
        profile_data: dict,
    ) -> dict[str, str]:
        """Generate per-dimension improvement advice based on answer patterns.

        Returns: {"communication": "advice text", "learning": "...", ...}
        """
        from backend.llm import llm_chat, parse_json_response, get_model

        # Build answer summary for LLM
        q_map = {q["id"]: q for q in questions}
        answer_details = []
        for ans in answers:
            q = q_map.get(ans.get("question_id", ""))
            if not q:
                continue
            opts = {o["id"]: o for o in q["options"]}
            best_opt = opts.get(ans.get("best", ""))
            worst_opt = opts.get(ans.get("worst", ""))
            answer_details.append({
                "dimension": q["dimension"],
                "scenario": q["scenario"][:80],
                "best_choice": best_opt["text"] if best_opt else "",
                "best_efficacy": best_opt["efficacy"] if best_opt else 0,
                "worst_choice": worst_opt["text"] if worst_opt else "",
                "worst_efficacy": worst_opt["efficacy"] if worst_opt else 0,
            })

        dim_summary = ", ".join(
            f"{dim}: {info['score']}分({info['level']})"
            for dim, info in dimensions.items()
        )

        skills = [s.get("name", "") for s in profile_data.get("skills", [])[:5]]

        prompt = f"""你是一个职业发展顾问。用户刚完成了一次软技能情境评估。

评估结果：{dim_summary}
用户技能背景：{', '.join(skills)}

作答详情：
{json.dumps(answer_details, ensure_ascii=False, indent=2)}

请为每个维度生成 50-100 字的改进建议。要求：
- 正向语气，指出具体行为模式（"你倾向于…"）
- 给出可操作建议（"可以尝试…"）
- 不要重复题目内容，总结行为模式
- 即使是"优秀"等级也给出进一步提升的方向

返回严格 JSON：
{{"communication": "建议文字", "learning": "建议文字", "collaboration": "建议文字"}}

只返回 JSON，不要有任何其他文字。"""

        try:
            result = llm_chat(
                [{"role": "user", "content": prompt}],
                model=get_model("default"),
                temperature=0.7,
                timeout=30,
            )
            advice = parse_json_response(result)
            if isinstance(advice, dict):
                return {k: str(v) for k, v in advice.items() if k in dimensions}
        except Exception:
            pass
        return {}
```

- [ ] **Step 2: Rewrite the submit endpoint in `profiles.py`**

Replace `SjtSubmitRequest` (line 435-437) and `submit_sjt` (lines 440-501) with:

```python
class SjtSubmitRequest(BaseModel):
    profile_id: int
    session_id: str
    answers: list[dict]  # [{"question_id": "t01", "best": "b", "worst": "c"}, ...]


@router.post("/sjt/submit")
def submit_sjt(
    req: SjtSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Score SJT v2 answers, generate advice, write back to profile."""
    from datetime import datetime, timezone
    from backend.db_models import SjtSession
    from backend.services.profile_service import ProfileService

    # Validate profile
    profile = (
        db.query(Profile)
        .filter(Profile.id == req.profile_id, Profile.user_id == user.id)
        .first()
    )
    if not profile:
        raise HTTPException(404, "画像不存在")

    # Validate session
    session = db.query(SjtSession).filter(SjtSession.id == req.session_id).first()
    if not session:
        raise HTTPException(410, "评估会话不存在，请重新开始")
    if session.profile_id != profile.id:
        raise HTTPException(400, "会话与画像不匹配")
    if session.expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise HTTPException(410, "评估已过期，请重新开始")

    # Validate answers
    questions = json.loads(session.questions_json)
    expected_ids = {q["id"] for q in questions}
    submitted_ids = {a.get("question_id") for a in req.answers}
    missing = expected_ids - submitted_ids
    if missing:
        raise HTTPException(400, f"缺少以下题目的回答: {', '.join(sorted(missing))}")

    # Score
    result = ProfileService.score_sjt_v2(req.answers, questions)
    dimensions = result["dimensions"]

    # Generate advice (non-blocking: failure doesn't block scoring)
    profile_data = json.loads(profile.profile_json or "{}")
    advice = ProfileService.generate_sjt_advice(dimensions, req.answers, questions, profile_data)

    # Build v2 soft_skills structure
    soft_skills = {"_version": 2}
    for dim, info in dimensions.items():
        soft_skills[dim] = {
            "score": info["score"],
            "level": info["level"],
            "advice": advice.get(dim, ""),
        }

    # Write back to profile
    profile_data["soft_skills"] = soft_skills
    profile.profile_json = json.dumps(profile_data, ensure_ascii=False, default=str)

    # Recompute quality
    quality_data = _compute_quality(profile_data)
    profile.quality_json = json.dumps(quality_data, ensure_ascii=False, default=str)

    # Clean up session
    db.delete(session)
    db.commit()

    # Compute overall level
    all_scores = [info["score"] for info in dimensions.values()]
    overall_score = round(sum(all_scores) / len(all_scores)) if all_scores else 0
    overall_level = ProfileService.score_to_level(overall_score)

    return ok({
        "dimensions": [
            {"key": dim, "level": info["level"], "advice": advice.get(dim, "")}
            for dim, info in dimensions.items()
        ],
        "overall_level": overall_level,
    })
```

- [ ] **Step 3: Update `_compute_quality` to support v2 soft_skills**

In `backend/routers/profiles.py`, replace the soft skills extraction in `_compute_quality` (lines 59-72):

Replace:
```python
    # Extract soft skill dimensions if present
    soft = profile_data.get("soft_skills", {})
    dimensions = []
    _DIM_ZH = {"innovation": "创新能力", "learning": "学习能力", "resilience": "抗压能力",
                "communication": "沟通能力", "internship": "实习能力"}
    for key, label in _DIM_ZH.items():
        val = soft.get(key)
        if isinstance(val, dict):
            score = val.get("score", 50)
        elif isinstance(val, (int, float)):
            score = val
        else:
            continue
        dimensions.append({"key": key, "label": label, "score": int(score)})
```

With:
```python
    # Extract soft skill dimensions if present
    soft = profile_data.get("soft_skills", {})
    dimensions = []
    if soft.get("_version") == 2:
        _DIM_ZH = {"communication": "沟通能力", "learning": "学习能力", "collaboration": "协作能力"}
    else:
        _DIM_ZH = {"innovation": "创新能力", "learning": "学习能力", "resilience": "抗压能力",
                    "communication": "沟通能力", "internship": "实习能力"}
    for key, label in _DIM_ZH.items():
        val = soft.get(key)
        if isinstance(val, dict):
            score = val.get("score", 50)
        elif isinstance(val, (int, float)):
            score = val
        else:
            continue
        dimensions.append({"key": key, "label": label, "score": int(score)})
```

- [ ] **Step 4: Commit**

```bash
git add backend/services/profile_service.py backend/routers/profiles.py
git commit -m "feat(sjt): rewrite submit endpoint with v2 scoring, advice generation, session validation"
```

---

### Task 5: Backend — Update resume parsing and job matching

**Files:**
- Modify: `backend/routers/profiles.py` (remove soft_skills from resume parse prompt)
- Modify: `backend/services/profile_service.py` (update `_score_qualities`, `_DEFAULT_SSW`)

- [ ] **Step 1: Remove soft_skills from resume parse prompt**

In `backend/routers/profiles.py`, replace `_RESUME_PARSE_PROMPT` (lines 162-199) with:

```python
_RESUME_PARSE_PROMPT = """你是一个简历解析 AI。请从以下简历文本中提取结构化信息，以 JSON 格式返回。

返回格式（严格 JSON，不要加注释或 markdown）：
{{
  "name": "姓名（可选）",
  "experience_years": 工作年限数字（无经验填0）,
  "education": {{"degree": "学位", "major": "专业", "school": "学校"}},
  "skills": [
    {{"name": "技能名称", "level": "expert|proficient|familiar|beginner"}}
  ],
  "knowledge_areas": ["知识领域1", "知识领域2"],
  "projects": ["项目描述1", "项目描述2"]
}}

技能等级说明：
- expert/advanced: 有深度项目经验，能独立解决复杂问题
- proficient/intermediate: 熟练使用，有实际项目经验
- familiar: 了解基础，做过简单使用
- beginner/entry: 学过但经验少

简历文本：
{resume_text}

只返回 JSON，不要有任何其他文字。"""
```

And in `_extract_profile_with_llm` (after line 214), add soft_skills v2 initialization. After `parsed.setdefault("projects", [])`:

```python
        # Initialize v2 soft_skills as unassessed
        parsed["soft_skills"] = {
            "_version": 2,
            "communication": None,
            "learning": None,
            "collaboration": None,
        }
```

- [ ] **Step 2: Update `_DEFAULT_SSW` and `_score_qualities` in `profile_service.py`**

Replace `_DEFAULT_SSW` (lines 123-126):

```python
_DEFAULT_SSW: dict[str, float] = {
    "communication": 0.35, "learning": 0.35, "collaboration": 0.30,
}
```

Replace `_score_qualities` (lines 989-1035):

```python
def _score_qualities(
    user_profile: dict[str, Any],
    graph_node: dict[str, Any] | None,
    sjt_scores: dict[str, float] | None,
) -> tuple[float, dict]:
    """Professional qualities — 3 sub-dimensions weighted by job soft_skill_weights."""
    ssw = (graph_node or {}).get("soft_skill_weights") or {}
    # Fallback: if old 5-dim weights or empty, use default 3-dim
    dims_v2 = ["communication", "learning", "collaboration"]
    if not all(d in ssw for d in dims_v2):
        ssw = _DEFAULT_SSW.copy()

    user_soft = user_profile.get("soft_skills", {})

    sub_scores: dict[str, float] = {}
    for dim in dims_v2:
        job_weight = ssw.get(dim, 0.33)

        # User score from soft_skills dict (v2 format)
        user_val = user_soft.get(dim)
        if isinstance(user_val, dict):
            user_score = user_val.get("score", 0) / 100.0
        elif isinstance(user_val, (int, float)):
            user_score = user_val / 100.0
        else:
            user_score = 0  # Not assessed yet

        # Match: user / job_requirement, capped at 1.0
        if job_weight > 0.05:
            match = _clamp01(user_score / job_weight)
        else:
            match = _clamp01(user_score)

        sub_scores[dim] = round(match * 100, 1)

    # Weighted average by job weights
    total_w = sum(ssw.get(d, 0.33) for d in dims_v2)
    if total_w > 0:
        score = sum(sub_scores[d] / 100.0 * ssw.get(d, 0.33) for d in dims_v2) / total_w
    else:
        score = sum(sub_scores[d] for d in dims_v2) / (100.0 * len(dims_v2))

    return score, {d: sub_scores[d] for d in dims_v2}
```

- [ ] **Step 3: Update `score_four_dimensions` docstring**

In `backend/services/profile_service.py`, update the docstring in `score_four_dimensions` (around line 1341-1342):

Replace:
```python
          qualities = 5 sub-dimensions weighted by soft_skill_weights
```

With:
```python
          qualities = 3 sub-dimensions (communication/learning/collaboration) weighted by soft_skill_weights
```

- [ ] **Step 4: Delete old `data/sjt_questions.json`**

```bash
rm data/sjt_questions.json
```

- [ ] **Step 5: Commit**

```bash
git add backend/routers/profiles.py backend/services/profile_service.py
git rm data/sjt_questions.json
git commit -m "feat(sjt): remove LLM soft skill inference from resume, update job matching to 3 dimensions"
```

---

### Task 6: Frontend — Update API layer

**Files:**
- Modify: `frontend/src/api/profiles.ts`

- [ ] **Step 1: Rewrite the profiles API types and functions**

Replace the SJT-related types and functions in `frontend/src/api/profiles.ts`. The file currently exports `SjtQuestion`, `SjtAnswer`, `SjtResult`, `fetchSjtQuestions`, `submitSjtAnswers`. Replace those with:

```typescript
// ── SJT v2 types ─────────────────────────────────────────────

export interface SjtQuestion {
  id: string
  dimension: string
  scenario: string
  options: Array<{ id: string; text: string }>
}

export interface SjtAnswer {
  question_id: string
  best: string
  worst: string
}

export interface SjtGenerateResult {
  session_id: string
  questions: SjtQuestion[]
}

export interface SjtDimensionResult {
  key: string
  level: string
  advice: string
}

export interface SjtSubmitResult {
  dimensions: SjtDimensionResult[]
  overall_level: string
}

export async function generateSjt(profileId: number): Promise<SjtGenerateResult> {
  const res = await rawFetch('/profiles/sjt/generate', {
    method: 'POST',
    body: JSON.stringify({ profile_id: profileId }),
  })
  return res.data
}

export async function submitSjt(
  profileId: number,
  sessionId: string,
  answers: SjtAnswer[],
): Promise<SjtSubmitResult> {
  const res = await rawFetch('/profiles/sjt/submit', {
    method: 'POST',
    body: JSON.stringify({ profile_id: profileId, session_id: sessionId, answers }),
  })
  return res.data
}
```

Delete `fetchSjtQuestions` if it still exists.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/profiles.ts
git commit -m "feat(frontend): update SJT API types and functions for v2"
```

---

### Task 7: Frontend — Rewrite SjtCtaCard

**Files:**
- Modify: `frontend/src/components/profile/SjtCtaCard.tsx`

- [ ] **Step 1: Rewrite SjtCtaCard with 5-phase flow**

Replace the entire content of `frontend/src/components/profile/SjtCtaCard.tsx`:

```tsx
import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ClipboardCheck, ChevronRight, Loader2, X } from 'lucide-react'
import { generateSjt, submitSjt } from '@/api/profiles'
import type { SjtQuestion, SjtAnswer, SjtDimensionResult } from '@/api/profiles'

const LEVEL_STYLE: Record<string, { bg: string; text: string }> = {
  '待发展': { bg: 'bg-slate-100', text: 'text-slate-600' },
  '基础': { bg: 'bg-blue-100', text: 'text-blue-700' },
  '良好': { bg: 'bg-emerald-100', text: 'text-emerald-700' },
  '优秀': { bg: 'bg-amber-100', text: 'text-amber-700' },
}

const DIM_LABEL: Record<string, string> = {
  communication: '沟通能力',
  learning: '学习能力',
  collaboration: '协作能力',
}

type Phase = 'cta' | 'generating' | 'answering' | 'submitting' | 'done'

interface Props {
  profileId: number
  onComplete: () => void
}

export default function SjtCtaCard({ profileId, onComplete }: Props) {
  const [phase, setPhase] = useState<Phase>('cta')
  const [sessionId, setSessionId] = useState('')
  const [questions, setQuestions] = useState<SjtQuestion[]>([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState<SjtAnswer[]>([])
  const [bestId, setBestId] = useState<string | null>(null)
  const [worstId, setWorstId] = useState<string | null>(null)
  const [results, setResults] = useState<SjtDimensionResult[]>([])
  const [overallLevel, setOverallLevel] = useState('')
  const [error, setError] = useState('')

  const handleStart = useCallback(async () => {
    setError('')
    setPhase('generating')
    try {
      const data = await generateSjt(profileId)
      setSessionId(data.session_id)
      setQuestions(data.questions)
      setCurrentIdx(0)
      setAnswers([])
      setPhase('answering')
    } catch (e) {
      setError(e instanceof Error ? e.message : '生成失败，请重试')
      setPhase('cta')
    }
  }, [profileId])

  const handleNext = useCallback(() => {
    if (!bestId || !worstId) return
    const q = questions[currentIdx]
    const newAnswers = [...answers, { question_id: q.id, best: bestId, worst: worstId }]
    setAnswers(newAnswers)
    setBestId(null)
    setWorstId(null)

    if (currentIdx + 1 < questions.length) {
      setCurrentIdx(currentIdx + 1)
    } else {
      // Submit
      setPhase('submitting')
      submitSjt(profileId, sessionId, newAnswers)
        .then((res) => {
          setResults(res.dimensions)
          setOverallLevel(res.overall_level)
          setPhase('done')
        })
        .catch((e) => {
          setError(e instanceof Error ? e.message : '提交失败，请重试')
          setPhase('answering')
        })
    }
  }, [bestId, worstId, questions, currentIdx, answers, profileId, sessionId])

  const handleOptionClick = (optionId: string, role: 'best' | 'worst') => {
    if (role === 'best') {
      setBestId(optionId === bestId ? null : optionId)
      if (optionId === worstId) setWorstId(null)
    } else {
      setWorstId(optionId === worstId ? null : optionId)
      if (optionId === bestId) setBestId(null)
    }
  }

  // ── Phase: CTA ──
  if (phase === 'cta') {
    return (
      <div className="glass p-6 text-center">
        <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center mx-auto mb-4">
          <ClipboardCheck className="w-6 h-6 text-[var(--blue)]" />
        </div>
        <h3 className="text-[16px] font-bold text-slate-800 mb-1">完成情境评估，了解你的软技能画像</h3>
        <p className="text-[13px] text-slate-500 mb-5">15 道基于你经历的情境题，约 5-8 分钟</p>
        {error && <p className="text-[13px] text-red-500 mb-3">{error}</p>}
        <button
          onClick={handleStart}
          className="btn-cta px-6 py-2.5 text-[14px] font-semibold cursor-pointer"
        >
          开始评估
        </button>
      </div>
    )
  }

  // ── Phase: Generating ──
  if (phase === 'generating') {
    return (
      <div className="glass p-6 flex items-center gap-4">
        <Loader2 className="w-6 h-6 text-[var(--blue)] animate-spin shrink-0" />
        <div>
          <p className="text-[14px] font-medium text-slate-700">正在根据你的经历生成个性化情境题...</p>
          <p className="text-[12px] text-slate-400 mt-0.5">这可能需要几秒钟</p>
        </div>
      </div>
    )
  }

  // ── Phase: Answering ──
  if (phase === 'answering') {
    const q = questions[currentIdx]
    return (
      <div className="glass p-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-[12px] font-semibold text-slate-400 uppercase tracking-wider">
            {DIM_LABEL[q.dimension] || q.dimension}
          </span>
          <span className="text-[12px] font-mono text-slate-400">
            {currentIdx + 1} / {questions.length}
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full h-1 bg-slate-100 rounded-full mb-5">
          <motion.div
            className="h-full bg-[var(--blue)] rounded-full"
            initial={false}
            animate={{ width: `${((currentIdx + 1) / questions.length) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>

        <p className="text-[14px] text-slate-700 leading-relaxed mb-5">{q.scenario}</p>

        {error && <p className="text-[13px] text-red-500 mb-3">{error}</p>}

        <div className="space-y-2.5 mb-5">
          {q.options.map((o) => {
            const isBest = bestId === o.id
            const isWorst = worstId === o.id
            return (
              <div
                key={o.id}
                className={`rounded-xl border p-3 transition-all ${
                  isBest
                    ? 'border-emerald-300 bg-emerald-50'
                    : isWorst
                    ? 'border-red-300 bg-red-50'
                    : 'border-slate-200 bg-white/50'
                }`}
              >
                <p className="text-[13px] text-slate-700 mb-2">{o.text}</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleOptionClick(o.id, 'best')}
                    className={`text-[11px] px-2.5 py-1 rounded-lg font-medium transition-all cursor-pointer ${
                      isBest
                        ? 'bg-emerald-500 text-white'
                        : 'bg-slate-100 text-slate-500 hover:bg-emerald-100 hover:text-emerald-700'
                    }`}
                  >
                    最佳
                  </button>
                  <button
                    onClick={() => handleOptionClick(o.id, 'worst')}
                    className={`text-[11px] px-2.5 py-1 rounded-lg font-medium transition-all cursor-pointer ${
                      isWorst
                        ? 'bg-red-500 text-white'
                        : 'bg-slate-100 text-slate-500 hover:bg-red-100 hover:text-red-700'
                    }`}
                  >
                    最差
                  </button>
                </div>
              </div>
            )
          })}
        </div>

        <button
          onClick={handleNext}
          disabled={!bestId || !worstId}
          className="btn-cta w-full py-2.5 text-[14px] font-semibold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
        >
          {currentIdx + 1 < questions.length ? '下一题' : '提交评估'}
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    )
  }

  // ── Phase: Submitting ──
  if (phase === 'submitting') {
    return (
      <div className="glass p-6 flex items-center gap-4">
        <Loader2 className="w-6 h-6 text-[var(--blue)] animate-spin shrink-0" />
        <div>
          <p className="text-[14px] font-medium text-slate-700">正在分析你的作答...</p>
          <p className="text-[12px] text-slate-400 mt-0.5">生成评估结果和改进建议</p>
        </div>
      </div>
    )
  }

  // ── Phase: Done ──
  const overallStyle = LEVEL_STYLE[overallLevel] || LEVEL_STYLE['待发展']
  return (
    <div className="glass p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-[16px] font-bold text-slate-800">评估完成</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[13px] text-slate-500">综合等级</span>
            <span className={`text-[12px] font-semibold px-2.5 py-0.5 rounded-lg ${overallStyle.bg} ${overallStyle.text}`}>
              {overallLevel}
            </span>
          </div>
        </div>
        <button
          onClick={onComplete}
          className="p-2 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <AnimatePresence>
        <div className="space-y-3">
          {results.map((dim, i) => {
            const style = LEVEL_STYLE[dim.level] || LEVEL_STYLE['待发展']
            return (
              <motion.div
                key={dim.key}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="rounded-xl border border-slate-150 bg-white/60 p-4"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[14px] font-semibold text-slate-700">
                    {DIM_LABEL[dim.key] || dim.key}
                  </span>
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-lg ${style.bg} ${style.text}`}>
                    {dim.level}
                  </span>
                </div>
                {dim.advice && (
                  <p className="text-[13px] text-slate-500 leading-relaxed">{dim.advice}</p>
                )}
              </motion.div>
            )
          })}
        </div>
      </AnimatePresence>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/profile/SjtCtaCard.tsx
git commit -m "feat(frontend): rewrite SjtCtaCard with 5-phase generate/answer/result flow"
```

---

### Task 8: Frontend — Rewrite SoftSkillsCard

**Files:**
- Modify: `frontend/src/components/profile/SoftSkillsCard.tsx`

- [ ] **Step 1: Rewrite SoftSkillsCard with level badges**

Replace the entire content of `frontend/src/components/profile/SoftSkillsCard.tsx`:

```tsx
import { Brain } from 'lucide-react'

const LEVEL_STYLE: Record<string, { bg: string; text: string }> = {
  '待发展': { bg: 'bg-slate-100', text: 'text-slate-600' },
  '基础': { bg: 'bg-blue-100', text: 'text-blue-700' },
  '良好': { bg: 'bg-emerald-100', text: 'text-emerald-700' },
  '优秀': { bg: 'bg-amber-100', text: 'text-amber-700' },
}

const DIM_LABEL: Record<string, string> = {
  communication: '沟通能力',
  learning: '学习能力',
  collaboration: '协作能力',
}

interface SoftSkills {
  _version?: number
  communication?: { score: number; level: string; advice: string } | null
  learning?: { score: number; level: string; advice: string } | null
  collaboration?: { score: number; level: string; advice: string } | null
}

interface Props {
  softSkills: SoftSkills | undefined
  onStartAssessment?: () => void
}

export default function SoftSkillsCard({ softSkills, onStartAssessment }: Props) {
  const isV2 = softSkills?._version === 2
  const dims = ['communication', 'learning', 'collaboration'] as const
  const hasData = isV2 && dims.some((d) => softSkills?.[d] != null)

  // Not assessed or old version
  if (!hasData) {
    return (
      <div className="glass p-5">
        <div className="flex items-center gap-2 mb-3">
          <Brain className="w-4 h-4 text-[var(--blue)]" />
          <h3 className="text-[14px] font-semibold text-slate-700">软技能画像</h3>
        </div>
        <p className="text-[13px] text-slate-500 mb-3">
          {isV2 ? '完成情境评估后，这里将展示你的软技能画像' : '评估系统已升级，请重新测评'}
        </p>
        {onStartAssessment && (
          <button
            onClick={onStartAssessment}
            className="text-[13px] font-semibold text-[var(--blue)] hover:underline cursor-pointer"
          >
            去评估
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="glass p-5">
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-4 h-4 text-[var(--blue)]" />
        <h3 className="text-[14px] font-semibold text-slate-700">软技能画像</h3>
      </div>
      <div className="space-y-3">
        {dims.map((key) => {
          const dim = softSkills?.[key]
          if (!dim) return null
          const style = LEVEL_STYLE[dim.level] || LEVEL_STYLE['待发展']
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="text-[13px] text-slate-600 w-16 shrink-0">{DIM_LABEL[key]}</span>
              <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-lg ${style.bg} ${style.text}`}>
                {dim.level}
              </span>
            </div>
          )
        })}
      </div>
      {onStartAssessment && (
        <button
          onClick={onStartAssessment}
          className="mt-4 text-[12px] text-slate-400 hover:text-[var(--blue)] transition-colors cursor-pointer"
        >
          重新评估
        </button>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify imports in ProfilePage still work**

Check that `ProfilePage.tsx` imports `SoftSkillsCard` and `SjtCtaCard` correctly. If they use named imports, update to default imports to match the new `export default`.

```bash
cd C:/Users/liu/Desktop/career-planning-agent && grep -n "SoftSkillsCard\|SjtCtaCard" frontend/src/pages/ProfilePage.tsx
```

Fix any import mismatches (named → default or vice versa).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/profile/SoftSkillsCard.tsx
git commit -m "feat(frontend): rewrite SoftSkillsCard with 3-dimension level badges"
```

---

### Task 9: Integration — Wire ProfilePage + verify end-to-end

**Files:**
- Modify: `frontend/src/pages/ProfilePage.tsx` (ensure SjtCtaCard/SoftSkillsCard receive correct props)

- [ ] **Step 1: Update ProfilePage to pass correct props**

Read `ProfilePage.tsx` to find where `SjtCtaCard` and `SoftSkillsCard` are rendered. Update:

1. `SjtCtaCard` must receive `profileId={activeProfileId}` and `onComplete={() => refetchProfile()}`
2. `SoftSkillsCard` must receive `softSkills={profileData?.soft_skills}` and `onStartAssessment={() => scrollToSjtCard()}`

The exact changes depend on ProfilePage's current structure. Read the file, identify the render locations, and update the props.

- [ ] **Step 2: Run TypeScript check**

```bash
cd C:/Users/liu/Desktop/career-planning-agent/frontend && npx tsc --noEmit
```

Expected: 0 errors. Fix any type mismatches.

- [ ] **Step 3: Run dev server and verify**

```bash
cd C:/Users/liu/Desktop/career-planning-agent/frontend && npm run dev
```

Manual verification:
1. Navigate to Profile page
2. SoftSkillsCard shows "评估系统已升级，请重新测评" (for existing profiles) or "完成情境评估后..." (for new)
3. Click "开始评估" → loading → 15 questions appear → answer all → results with levels + advice

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ProfilePage.tsx
git commit -m "feat(frontend): wire ProfilePage to v2 SJT assessment components"
```

---

### Task 10: Cleanup — Remove dead code

**Files:**
- Modify: `backend/services/profile_service.py` (remove `_load_sjt_questions` if any leftover references)
- Verify: No remaining references to old 5-dimension constants

- [ ] **Step 1: Search for dead references**

```bash
cd C:/Users/liu/Desktop/career-planning-agent
grep -rn "fuse_with_llm\|_load_sjt_questions\|fetchSjtQuestions\|innovation.*resilience\|internship" --include="*.py" --include="*.ts" --include="*.tsx" | grep -v node_modules | grep -v .venv | grep -v sjt_questions.json
```

Remove any remaining references found.

- [ ] **Step 2: Verify backend starts cleanly**

```bash
cd C:/Users/liu/Desktop/career-planning-agent && python -c "from backend.app import create_app; app = create_app(); print('OK: app starts')"
```

- [ ] **Step 3: Verify frontend compiles**

```bash
cd C:/Users/liu/Desktop/career-planning-agent/frontend && npx tsc --noEmit && echo "OK: no type errors"
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove dead v1 SJT code and old 5-dimension references"
```
