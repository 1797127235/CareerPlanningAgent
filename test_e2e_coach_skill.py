"""端到端场景验证脚本 — 直接调用 coach_agent（绕过路由，专注验证 T1-T4）。"""
from __future__ import annotations

import asyncio
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from agent.agents.coach_agent import BASE_IDENTITY, create_coach_agent
from agent.skills.loader import format_skills_for_prompt
from agent.supervisor import build_context_summary
from agent.tools.coach_context_tools import (
    _ctx_profile, _ctx_goal, _ctx_user_id, _ctx_market_loader,
)
from agent.supervisor import _get_market_signal_for_node

PROFILE = {
    "skills": [
        {"name": "Python"},
        {"name": "C++"},
        {"name": "数据结构"},
    ],
    "education": {"degree": "本科", "major": "计算机科学"},
    "projects": [
        {"name": "Web服务器", "description": "基于C++的高并发HTTP服务器"},
    ],
    "preferences": {
        "work_style": "tech",
        "value_priority": "growth",
        "company_type": "big_tech",
        "current_stage": "lost",
    },
    "job_target": "后端开发",
}

GOAL = {
    "label": "后端开发",
    "node_id": "cs_system_cpp",
    "zone": "thrive",
}


def make_sys_prompt(msgs: list) -> str:
    state = {
        "messages": msgs,
        "user_stage": "lost",
        "career_goal": GOAL,
        "user_profile": PROFILE,
    }
    context = build_context_summary(state, agent_name="coach_agent")
    skills = format_skills_for_prompt()
    return BASE_IDENTITY.replace("{AVAILABLE_SKILLS}", skills).replace("{CONTEXT}", context)


async def run_coach_turn(msgs: list) -> tuple[str, list[dict]]:
    """调用 coach_agent，注入 ContextVar，返回 AI 文本 + 工具调用列表。"""
    agent = create_coach_agent()
    sys_prompt = make_sys_prompt(msgs)
    input_msgs = [SystemMessage(content=sys_prompt)] + msgs

    tok_p = _ctx_profile.set(PROFILE)
    tok_g = _ctx_goal.set(GOAL)
    tok_u = _ctx_user_id.set(1)
    tok_m = _ctx_market_loader.set(_get_market_signal_for_node)

    full_text = ""
    tool_calls_by_id: dict[str, dict] = {}
    tool_results: list[dict] = []

    try:
        async for msg_chunk, metadata in agent.astream(
            {"messages": input_msgs},
            stream_mode="messages",
        ):
            from langchain_core.messages import ToolMessage, SystemMessage as LCSystemMessage
            if isinstance(msg_chunk, ToolMessage):
                tool_results.append({
                    "name": getattr(msg_chunk, "name", ""),
                    "content": str(getattr(msg_chunk, "content", ""))[:300],
                })
                continue
            if isinstance(msg_chunk, (LCSystemMessage, HumanMessage)):
                continue

            # 聚合 tool call 请求（按 id 合并，避免流式 chunk 导致 name 为空）
            tcs = getattr(msg_chunk, "tool_calls", None)
            if tcs:
                for tc in tcs:
                    tid = tc.get("id", "")
                    if tid not in tool_calls_by_id:
                        tool_calls_by_id[tid] = {"name": tc.get("name", ""), "args": tc.get("args", {})}
                    else:
                        if tc.get("name"):
                            tool_calls_by_id[tid]["name"] = tc["name"]
                        if tc.get("args"):
                            tool_calls_by_id[tid]["args"].update(tc["args"])
                continue

            content = getattr(msg_chunk, "content", "")
            if content:
                full_text += content
    finally:
        for var, tok in [(_ctx_profile, tok_p), (_ctx_goal, tok_g), (_ctx_user_id, tok_u), (_ctx_market_loader, tok_m)]:
            try:
                var.reset(tok)
            except Exception:
                pass

    all_tools = list(tool_calls_by_id.values()) + tool_results
    return full_text, all_tools


async def main():
    print("=" * 60)
    print("端到端场景验证开始（直接调用 coach_agent）")
    print("=" * 60)

    # ── 场景 A：冷启动问候（第 1 轮）─────────────────────────────
    print("\n【场景 A】输入：你好")
    msgs_a = [HumanMessage(content="你好")]
    text_a, tools_a = await run_coach_turn(msgs_a)
    print(f"回复：{text_a}")
    print(f"工具调用：{tools_a}")

    forbidden = ["方向迷茫", "C++基础扎实", "大厂偏好", "深挖技术", "就业意愿"]
    has_forbidden = any(w in text_a for w in forbidden)
    sentences = [s.strip() for s in text_a.replace("?", "。").replace("？", "。").split("。") if s.strip()]
    has_question = "?" in text_a or "？" in text_a or any(s.endswith(("吗", "么", "什么", "哪个", "怎")) for s in sentences)

    ok_a = len(sentences) <= 5 and not has_forbidden and has_question
    print(f"  -> 句数:{len(sentences)}, 含禁用词:{has_forbidden}, 含开放问题:{has_question}")
    print(f"  -> 场景 A {'PASS' if ok_a else 'FAIL'}")

    # ── 场景 B：担忧表达（第 2 轮）─────────────────────────────────
    print("\n【场景 B】输入：我不知道我现在的技术能不能找到工作")
    msgs_b = [
        HumanMessage(content="你好"),
        HumanMessage(content="我不知道我现在的技术能不能找到工作"),
    ]
    text_b, tools_b = await run_coach_turn(msgs_b)
    print(f"回复：{text_b}")
    print(f"工具调用：{json.dumps(tools_b, ensure_ascii=False, indent=2)}")

    tool_names_b = [t.get("name", "") for t in tools_b]
    has_profile_call = "get_user_profile" in tool_names_b
    has_market_call = "get_market_signal" in tool_names_b
    no_rhetorical = "你觉得呢" not in text_b and "你怎么看" not in text_b and "你的理解是什么" not in text_b

    ok_b = has_profile_call and has_market_call and no_rhetorical
    print(f"  -> get_user_profile:{has_profile_call}, get_market_signal:{has_market_call}, 无反问:{no_rhetorical}")
    print(f"  -> 场景 B {'PASS' if ok_b else 'FAIL'}")

    # ── 场景 C：具体请求（第  轮）─────────────────────────────────
    print("\n【场景 C】输入：帮我梳理一下")
    msgs_c = [
        HumanMessage(content="你好"),
        HumanMessage(content="我不知道我现在的技术能不能找到工作"),
        HumanMessage(content="帮我梳理一下"),
    ]
    text_c, tools_c = await run_coach_turn(msgs_c)
    print(f"回复：{text_c}")
    print(f"工具调用：{json.dumps(tools_c, ensure_ascii=False, indent=2)}")

    tool_names_c = [t.get("name", "") for t in tools_c]
    has_profile_call_c = "get_user_profile" in tool_names_c
    no_rhetorical_c = "你觉得呢" not in text_c and "你怎么看" not in text_c and "你的理解是什么" not in text_c

    ok_c = has_profile_call_c and no_rhetorical_c
    print(f"  -> get_user_profile:{has_profile_call_c}, 无反问:{no_rhetorical_c}")
    print(f"  -> 场景 C {'PASS' if ok_c else 'FAIL'}")

    print("\n" + "=" * 60)
    if ok_a and ok_b and ok_c:
        print("全部通过")
        return 0
    else:
        print("存在失败场景")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
