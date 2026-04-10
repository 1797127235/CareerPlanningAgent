"""
为 graph.json 的 34 个岗位节点生成软技能维度数据。

5 维度（1-5 分制）：
  - communication（沟通能力）
  - learning（学习能力）
  - resilience（抗压能力）
  - innovation（创新能力）
  - collaboration（协作能力）

推导逻辑：
  基于 career_level / replacement_pressure / human_ai_leverage / role_family / zone
  + 岗位特性微调
"""
import json, math
from pathlib import Path

GRAPH_PATH = Path(__file__).resolve().parent.parent / "data" / "graph.json"

# ---------- 岗位特性覆盖 ----------
# 只写需要偏离公式默认值的维度
OVERRIDES: dict[str, dict[str, int]] = {
    # 管理/架构角色：沟通、协作拉满
    "software-architect":   {"communication": 5, "collaboration": 5, "innovation": 5},
    "engineering-manager":  {"communication": 5, "collaboration": 5, "resilience": 5},
    # 全栈/跨职能
    "full-stack":           {"collaboration": 4, "communication": 4, "learning": 5},
    # AI / 研究型 — 竞争激烈，抗压不能太低
    "ai-engineer":          {"innovation": 5, "learning": 5, "resilience": 3},
    "machine-learning":     {"innovation": 5, "learning": 5, "resilience": 3},
    # 安全 / 运维 — 抗压高
    "cyber-security":       {"resilience": 5, "learning": 5},
    "devsecops":            {"resilience": 5, "collaboration": 4},
    "devops":               {"resilience": 5, "collaboration": 4},
    "kubernetes":           {"resilience": 4, "collaboration": 4},
    # 游戏 — 创新+抗压
    "game-developer":       {"innovation": 5, "resilience": 4},
    # 数据分析 — 沟通（面向业务）
    "data-analyst":         {"communication": 4, "collaboration": 4},
    # QA — 沟通+协作（跨团队验收）+ 需学测试框架/工具
    "qa":                   {"communication": 4, "collaboration": 4, "learning": 3, "innovation": 2},
}

def clamp(v: float, lo: int = 1, hi: int = 5) -> int:
    return max(lo, min(hi, round(v)))


def compute_soft_skills(node: dict) -> dict[str, int]:
    cl = node.get("career_level", 2)
    rp = node.get("replacement_pressure", 40)
    hal = node.get("human_ai_leverage", 60)
    family = node.get("role_family", "")
    nid = node["node_id"]

    # --- 沟通能力 ---
    # 基础来自 career_level；管理/分析 +1
    comm = cl
    if family in ("management",):
        comm += 1
    if family in ("data_analysis",):
        comm += 1
    comm = clamp(comm)

    # --- 学习能力 ---
    # 高 human_ai_leverage 的领域技术迭代快，需要持续学习
    # 归一到 1-5
    learn = 1 + (hal - 50) / 12.5  # 50→1, 62.5→2, 75→3, 87.5→4, 100→5
    learn = max(learn, cl - 1)      # 高级别最低不低于 cl-1
    learn = clamp(learn)

    # --- 抗压能力 ---
    # 替代压力高 → 需要更强抗压
    # 安全/运维/高级别 额外加分
    resil = 1 + (rp - 10) / 15  # 10→1, 25→2, 40→3, 55→4, 70→5
    if family in ("devops_infra",):
        resil += 0.5
    if cl >= 4:
        resil += 0.5
    resil = clamp(resil)

    # --- 创新能力 ---
    # human_ai_leverage 高 → 人类创造力溢价 → 创新需求高
    innov = 1 + (hal - 50) / 12.5
    if family in ("algorithm_ai",):
        innov += 1
    innov = clamp(innov)

    # --- 协作能力 ---
    # career_level 高 → 更多跨团队协作
    # 管理/运维/全栈 天然跨职能
    collab = cl
    if family in ("management",):
        collab += 1
    if family in ("devops_infra",):
        collab += 0.5
    collab = clamp(collab)

    result = {
        "communication": comm,
        "learning": learn,
        "resilience": resil,
        "innovation": innov,
        "collaboration": collab,
    }

    # 应用特性覆盖
    if nid in OVERRIDES:
        result.update(OVERRIDES[nid])

    return result


def main():
    raw = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    for node in raw["nodes"]:
        node["soft_skills"] = compute_soft_skills(node)
        print(f"  {node['label']:20s} → {node['soft_skills']}")
    GRAPH_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nDone: wrote soft_skills for {len(raw['nodes'])} nodes")


if __name__ == "__main__":
    main()
