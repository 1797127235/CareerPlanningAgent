"""Stage-aware greeting builder for the chat panel."""
from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import CareerGoal, InterviewRecord, JDDiagnosis, JobApplication, Profile, ProjectRecord, Report
from backend.services.chat.market_cards import get_card_for_node
from backend.services.growth.stage import compute_stage

if TYPE_CHECKING:
    from backend.models import User

logger = logging.getLogger(__name__)

# Lazy graph node cache for greeting builder
_CHAT_GRAPH_NODES: dict | None = None
_CHAT_GRAPH_MTIME: float = 0.0


def _get_graph_nodes() -> dict:
    """Lightweight graph node cache — avoids importing profiles module."""
    global _CHAT_GRAPH_NODES, _CHAT_GRAPH_MTIME
    graph_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", "graph.json"
    )
    try:
        mtime = os.path.getmtime(graph_path)
    except OSError:
        mtime = 0.0
    if _CHAT_GRAPH_NODES is None or mtime != _CHAT_GRAPH_MTIME:
        try:
            with open(graph_path, "r", encoding="utf-8") as f:
                nodes = json.load(f).get("nodes", [])
            _CHAT_GRAPH_NODES = {n["node_id"]: n for n in nodes}
            _CHAT_GRAPH_MTIME = mtime
        except Exception:
            _CHAT_GRAPH_NODES = {}
    return _CHAT_GRAPH_NODES or {}


def build_greeting(user: "User", db: Session) -> dict:
    """Build a stage-aware greeting + dynamic action chips for the chat panel."""
    # Gather user state
    profile = (
        db.query(Profile)
        .filter_by(user_id=user.id)
        .order_by(Profile.updated_at.desc())
        .first()
    )
    profile_name = "同学"
    skill_count = 0
    profile_data: dict = {}
    if profile:
        profile_name = profile.name or "同学"
        try:
            profile_data = json.loads(profile.profile_json or "{}")
        except (json.JSONDecodeError, TypeError):
            pass
        skill_count = len(profile_data.get("skills", []))

    goal = (
        db.query(CareerGoal)
        .filter(
            CareerGoal.user_id == user.id,
            CareerGoal.is_active == True,  # noqa: E712
            CareerGoal.target_node_id != "",
        )
        .order_by(CareerGoal.set_at.desc())
        .first()
    )

    profile_count = db.query(func.count(Profile.id)).filter_by(user_id=user.id).scalar() or 0
    jd_count = db.query(func.count(JDDiagnosis.id)).filter_by(user_id=user.id).scalar() or 0
    project_count = db.query(func.count(ProjectRecord.id)).filter_by(user_id=user.id).scalar() or 0
    app_count = db.query(func.count(JobApplication.id)).filter_by(user_id=user.id).scalar() or 0
    interview_count = db.query(func.count(InterviewRecord.id)).filter_by(user_id=user.id).scalar() or 0
    activity_count = project_count + app_count + interview_count
    report_count = db.query(func.count(Report.id)).filter_by(user_id=user.id).scalar() or 0

    stage = compute_stage(profile_count, jd_count, activity_count, report_count)

    # Guard: auto-created empty profiles inflate profile_count to 1 even with no content.
    if stage == "has_profile":
        has_real_content = (
            skill_count > 0
            or bool(profile_data.get("name", "").strip())
            or bool(profile_data.get("raw_text", ""))
            or len(profile_data.get("knowledge_areas", [])) > 0
            or len(profile_data.get("projects", [])) > 0
        )
        if not has_real_content:
            stage = "no_profile"

    # Detect "processing" state
    recs_ready = False
    if stage == "has_profile" and profile:
        try:
            cached = json.loads(profile.cached_recs_json or "{}")
            recs_ready = bool(cached.get("data", {}).get("recommendations"))
        except (json.JSONDecodeError, TypeError):
            recs_ready = False

    # Latest JD diagnosis info
    latest_jd_score = None
    gap_count = 0
    if jd_count > 0:
        latest_jd = (
            db.query(JDDiagnosis)
            .filter_by(user_id=user.id)
            .order_by(JDDiagnosis.created_at.desc())
            .first()
        )
        if latest_jd:
            latest_jd_score = latest_jd.match_score
            try:
                result = json.loads(latest_jd.result_json or "{}")
                gap_count = len(result.get("gap_skills", []))
            except (json.JSONDecodeError, TypeError):
                pass

    learning_pct = 0
    greeting = ""
    chips: list[dict] = []

    if stage == "no_profile":
        greeting = (
            f"嗨！我是你的智析教练。\n\n"
            f"我们先从了解你开始——上传一份简历，我帮你做能力画像和方向分析。"
        )
        chips = [
            {"label": "这个系统能做什么？", "prompt": "介绍一下你的功能"},
            {"label": "我是计算机专业学生", "prompt": "我是计算机专业的大三学生，不知道该找什么方向的工作"},
            {"label": "前端和后端怎么选", "prompt": "前端和后端该怎么选？"},
        ]

    elif stage == "has_profile" and not goal:
        if not recs_ready:
            greeting = (
                f"简历解析完成，{profile_name}！我正在分析你的技能背景并匹配最适合的方向，"
                f"通常需要十几秒——稍后刷新就能看到结果。\n\n"
                f"你也可以先告诉我你感兴趣的方向，我来帮你分析。"
            )
            chips = [
                {"label": "我对后端开发感兴趣", "prompt": "我对后端开发方向感兴趣，帮我分析适不适合"},
                {"label": "我对AI/大模型感兴趣", "prompt": "我对AI和大模型方向感兴趣，帮我分析"},
                {"label": "帮我解释这个系统能做什么", "prompt": "介绍一下这个系统能帮我做什么"},
            ]
        else:
            job_target = profile_data.get("job_target", "").strip()
            if job_target:
                greeting = (
                    f"画像建好了，{profile_name}！我看到你的求职意向是「{job_target}」。\n\n"
                    f"先别急着定目标——让我帮你分析这个方向的真实市场情况和你的差距，看清楚再做决定。"
                )
                chips = [
                    {"label": f"分析「{job_target}」方向", "prompt": f"帮我深入分析{job_target}这个方向，市场需求、薪资范围和我的差距"},
                    {"label": "这个方向竞争激烈吗", "prompt": f"{job_target}这个方向的就业竞争情况怎么样？"},
                    {"label": "还有哪些相似方向", "prompt": f"和{job_target}相似或相关的职业方向有哪些，帮我对比一下"},
                ]
            else:
                top_rec = None
                top_zone = None
                top_entry_barrier = None
                try:
                    cached = json.loads(profile.cached_recs_json or "{}")
                    recs_list = cached.get("data", {}).get("recommendations", [])
                    if recs_list:
                        top_rec = recs_list[0]
                        graph_nodes = _get_graph_nodes()
                        node_data = graph_nodes.get(top_rec.get("role_id", ""), {})
                        top_zone = node_data.get("zone", "")
                        top_entry_barrier = node_data.get("entry_barrier", "")
                except (json.JSONDecodeError, TypeError):
                    pass

                if top_rec:
                    top_label = top_rec.get("label") or top_rec.get("role_id", "")
                    top_pct = top_rec.get("affinity_pct", 0)

                    if top_zone == "danger":
                        signal = (
                            f"不过我要提前跟你说一件事：这个方向目前受 AI 自动化冲击比较大，"
                            f"市场需求在收缩。你想先听听我的分析，还是也看看相近的替代方向？"
                        )
                        chips = [
                            {"label": f"告诉我「{top_label}」的具体风险", "prompt": f"帮我分析{top_label}这个方向的AI替代风险和市场现状"},
                            {"label": "有没有更稳的替代方向", "prompt": f"和{top_label}相近但更有前景的方向有哪些？"},
                            {"label": "我就想做这个，怎么出圈", "prompt": f"如果坚持做{top_label}，怎么在竞争中建立差异化？"},
                        ]
                    elif top_zone == "transition":
                        signal = (
                            f"这个方向的市场正在转型期——需求结构在变化，"
                            f"了解清楚再决定会更稳妥。你想深入聊聊吗？"
                        )
                        chips = [
                            {"label": f"「{top_label}」方向怎么转型", "prompt": f"{top_label}这个方向市场正在如何转变，我该怎么准备？"},
                            {"label": "告诉我为什么推荐这个", "prompt": f"为什么「{top_label}」最匹配我？帮我分析原因"},
                            {"label": "还有哪些更稳的方向", "prompt": "有没有比这个更稳定的方向值得考虑？"},
                        ]
                    elif top_entry_barrier in ("low",):
                        signal = (
                            f"这个方向进入门槛相对低，竞争者也多——"
                            f"你想了解一下怎么在里面建立差异化吗？"
                        )
                        chips = [
                            {"label": f"告诉我为什么推荐「{top_label}」", "prompt": f"为什么「{top_label}」最匹配我？帮我分析"},
                            {"label": "怎么在这个方向出圈", "prompt": f"{top_label}方向竞争激烈，怎么让我的背景脱颖而出？"},
                            {"label": "有没有竞争更少的方向", "prompt": "有没有需求不错但竞争相对没那么大的方向？"},
                        ]
                    else:
                        signal = f"你怎么看这个方向？可以告诉我你的想法，我们来聊聊。"
                        chips = [
                            {"label": f"告诉我为什么推荐「{top_label}」", "prompt": f"为什么「{top_label}」最匹配我？详细分析一下"},
                            {"label": "看看其他推荐方向", "prompt": "帮我看看完整的推荐方向列表，对比一下各个选项"},
                            {"label": "这个方向市场需求怎么样", "prompt": f"「{top_label}」的市场需求、薪资水平和发展前景怎么样？"},
                        ]

                    greeting = (
                        f"分析完了，{profile_name}！"
                        f"根据你的背景，我觉得「{top_label}」最适合你（匹配度 {top_pct}%）。\n\n"
                        f"{signal}"
                    )
                else:
                    greeting = (
                        f"画像建好了，{profile_name}！我识别到你有 {skill_count} 项技能。\n\n"
                        f"你有感兴趣的方向吗？或者让我帮你分析最匹配的。"
                    )
                    chips = [
                        {"label": "帮我分析最匹配的方向", "prompt": "根据我的技能和项目背景，帮我分析最匹配的职业方向，解释为什么"},
                        {"label": "我对某个方向感兴趣", "prompt": "我对一个职业方向感兴趣，想了解更多"},
                        {"label": "我还不确定方向怎么办", "prompt": "我现在完全不知道该往哪个方向发展，帮我理清思路"},
                    ]

    elif stage == "has_profile" and goal:
        greeting = (
            f"{profile_name}，你已经把「{goal.target_label}」设为成长方向了。\n\n"
            f"下一步最有价值的事：找一份这个方向的真实 JD，粘贴过来做匹配度诊断——"
            f"看清楚你和岗位的真实差距，比猜测有用得多。"
        )
        chips = [
            {"label": "诊断一份JD", "prompt": "诊断 JD 匹配度"},
            {"label": f"成为{goal.target_label}核心要什么", "prompt": f"成为{goal.target_label}最核心的技能和经验是什么？"},
            {"label": "我现在差距有多大", "prompt": f"基于我的画像，我距离{goal.target_label}的差距主要在哪几块？"},
        ]

    elif stage == "first_diagnosis":
        score_part = f"匹配度 {latest_jd_score}%，" if latest_jd_score else ""
        gap_part = f"发现 {gap_count} 个技能缺口" if gap_count else "发现了一些技能缺口"
        greeting = (
            f"上次 JD 诊断{score_part}{gap_part}。\n\n"
            f"一份 JD 的数据太少，多诊断几份才能看清市场的真实要求——不同公司、不同规模的 JD 差异很大。"
        )
        chips = [
            {"label": "再诊断一份JD", "prompt": "诊断 JD 匹配度"},
            {"label": "我的缺口怎么补", "prompt": "帮我看看目前最大的技能缺口，以及补齐的思路"},
            {"label": "找找更多同类岗位JD", "prompt": "帮我搜索一些我目标方向的招聘信息，看看市场要求"},
        ]

    elif stage == "training":
        greeting = (
            f"你已经诊断了 {jd_count} 份 JD，对市场要求有了初步感知。\n\n"
            f"下一步可以做技能校准——用一两道面试题测测自己的真实水平，"
            f"或者继续扩大 JD 样本，看看不同公司的差异。"
        )
        chips = [
            {"label": "出一道题校准一下", "prompt": "出一道面试题校准一下，不用太难，帮我了解自己的真实水平"},
            {"label": "再诊断一份JD", "prompt": "诊断 JD 匹配度"},
            {"label": "看看成长数据", "prompt": "查看我的成长数据和进度"},
        ]

    elif stage == "growing":
        greeting = (
            f"你已经积累了 {jd_count} 次诊断，数据很扎实了！\n\n"
            f"现在可以生成一份职业发展报告，把你的能力画像、市场差距和成长轨迹系统梳理一下。"
        )
        chips = [
            {"label": "生成职业报告", "prompt": "帮我生成职业分析报告"},
            {"label": "看看成长看板", "prompt": "查看我的成长数据"},
            {"label": "再诊断一份JD", "prompt": "诊断 JD 匹配度"},
        ]

    else:  # report_ready
        lp = f"学习进度 {learning_pct}%，" if learning_pct > 0 else ""
        greeting = (
            f"你的职业规划闭环已经跑通了！{lp}继续保持。\n\n"
            f"可以做新的诊断、更新画像，或者聊聊下一阶段的发展方向。"
        )
        chips = [
            {"label": "做新的JD诊断", "prompt": "诊断 JD 匹配度"},
            {"label": "更新职业报告", "prompt": "帮我生成职业分析报告"},
            {"label": "聊聊下一步", "prompt": "我接下来应该重点提升什么能力？"},
        ]

    # Inject market card for target direction (if user has a goal)
    market_card = None
    if goal and goal.target_node_id:
        market_card = get_card_for_node(goal.target_node_id)

    is_processing = (stage == "has_profile" and not goal and not recs_ready)

    return {
        "stage": stage,
        "greeting": greeting,
        "chips": chips,
        "market_card": market_card,
        "processing": is_processing,
        "has_profile": stage != "no_profile",
        "context": {
            "profile_name": profile_name,
            "skill_count": skill_count,
            "goal_label": goal.target_label if goal else None,
            "jd_count": jd_count,
            "learning_pct": learning_pct,
        },
    }
