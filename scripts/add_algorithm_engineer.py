"""
Add 算法工程师 node to graph.json, role_intros.json, roadmap_skills.json.

Data sources:
  - O*NET 15-2051.00 (Data Scientists) — onet_cn_index.json confirmed
  - AEI (Anthropic Economic Index) — replacement_pressure calibrated against ML engineer (34.0)
  - developer-roadmap (machine-learning) — skill tree reference
  - 智联招聘 岗位数据.csv — salary reference (4.5-5万 for 科研算法方向)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

NEW_NODE = {
    "node_id": "algorithm-engineer",
    "label": "算法工程师",
    "role_family": "AI/ML",
    "zone": "thrive",
    "career_level": 3,
    "replacement_pressure": 29.0,
    "human_ai_leverage": 76.5,
    "onet_codes": ["15-2051.00"],
    "must_skills": [
        "Python",
        "机器学习",
        "PyTorch",
        "数学基础",
        "Scikit-learn",
        "SQL"
    ],
    "description": (
        "算法工程师专注于设计、研究和落地核心机器学习算法，深耕推荐系统、搜索排序、"
        "风险控制、异常检测、NLP、计算机视觉等垂直领域，将学术研究成果工程化为业务价值。"
        "通常要求较强的数学基础与论文阅读/复现能力。"
    ),
    "core_tasks": [
        "深研垂直领域算法（推荐/搜索/风控/异常检测），设计算法改进方案",
        "离线实验：特征工程、模型调优、消融实验，建立严格评估体系",
        "追踪前沿论文（ICML/NeurIPS/KDD），将学术成果工程化落地",
        "设计并执行 A/B 测试，量化算法效果并推动上线",
        "与业务/数据/工程团队协作，输出算法方案文档与实验报告"
    ],
    "soft_skills": {
        "communication": 3,
        "learning": 5,
        "resilience": 4,
        "innovation": 5,
        "collaboration": 3
    },
    "salary_p50": 40000,
    "promotion_path": [
        {"level": 1, "title": "算法工程师"},
        {"level": 2, "title": "高级算法工程师"},
        {"level": 3, "title": "算法专家 / 技术专家"},
        {"level": 4, "title": "资深算法架构师"},
        {"level": 5, "title": "首席科学家 / 研究员"}
    ],
    "routine_score": 35,
    "is_milestone": False,
    "skill_count": 6,
    "related_majors": ["计算机科学", "数学", "统计学", "人工智能", "信息与计算科学"],
    "min_experience": 0,
    "market_insight": (
        "算法工程师是大厂竞争最激烈的岗位，头部公司（字节/阿里/腾讯/快手）每年校招名额有限。"
        "2025-2026年趋势：LLM重塑推荐/搜索需求激增；风控/安全异常检测持续刚需；"
        "有 CCF/顶会论文或 Kaggle 金牌的候选人优先级显著更高。"
    ),
    "ai_impact_narrative": (
        "算法工程师受 AI 辅助最深——AutoML、Copilot 大幅压缩实验周期。"
        "核心不可替代性在于：定义评估指标需业务理解；算法创新需数学直觉；"
        "A/B 实验设计涉及复杂业务逻辑。定位应为"领域算法设计者"而非"调参员"。"
    ),
    "differentiation_advice": (
        "最有效路径：(1) 发表 CCF-B 及以上一作论文；"
        "(2) Kaggle/KDD Cup 金牌；"
        "(3) 在 GitHub 开源算法实现，附完整实验报告（datasets/baselines/消融实验/结果表格）。"
    ),
    "typical_employers": [
        "字节跳动", "阿里巴巴", "腾讯", "快手", "百度",
        "美团", "蚂蚁集团", "京东", "华为", "网易"
    ],
    "entry_barrier": "very_high",
    "career_ceiling": (
        "算法工程师薪资是 CS 最高档。应届 40-70 万（顶会论文 sp/ssp 更高），"
        "3 年资深算法 80-150 万，5 年算法专家 150-250 万+。"
    ),
    "project_recommendations": [
        {
            "name": "异常检测系统（开源代码 + 论文复现）",
            "why": (
                "将算法开源并在 PyOD benchmark 数据集上做完整对比实验（vs COF/IForest/OCSVM），"
                "写技术报告发布在 GitHub/arXiv，是最强求职信号。"
            ),
            "difficulty": "hard"
        },
        {
            "name": "推荐系统（双塔召回 + 精排）从零实现",
            "why": (
                "推荐算法是大厂最大算法岗需求来源。用 MovieLens/Amazon 数据集实现双塔召回+DIEN精排，"
                "做完整实验对比，能讲清楚 loss 设计取舍的候选人面试必赢。"
            ),
            "difficulty": "hard"
        }
    ]
}

# New edges to add
NEW_EDGES = [
    {"source": "machine-learning",   "target": "algorithm-engineer", "edge_type": "lateral"},
    {"source": "algorithm-engineer", "target": "machine-learning",   "edge_type": "lateral"},
    {"source": "ai-data-scientist",  "target": "algorithm-engineer", "edge_type": "lateral"},
    {"source": "algorithm-engineer", "target": "ai-data-scientist",  "edge_type": "lateral"},
    {"source": "ai-engineer",        "target": "algorithm-engineer", "edge_type": "lateral"},
    {"source": "algorithm-engineer", "target": "ml-architect",       "edge_type": "vertical"},
]


def update_graph_json():
    path = DATA / "graph.json"
    with open(path, encoding="utf-8") as f:
        graph = json.load(f)

    existing = {n["node_id"] for n in graph["nodes"]}
    if "algorithm-engineer" in existing:
        print("graph.json: 节点已存在，跳过")
        return

    graph["nodes"].append(NEW_NODE)

    valid = {n["node_id"] for n in graph["nodes"]}
    added = 0
    for e in NEW_EDGES:
        if e["source"] in valid and e["target"] in valid:
            graph["edges"].append(e)
            added += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    print(f"graph.json: 节点已添加 | 总节点 {len(graph['nodes'])} | 总边 {len(graph['edges'])} (+{added}条新边)")


def update_role_intros():
    path = DATA / "role_intros.json"
    with open(path, encoding="utf-8") as f:
        intros = json.load(f)

    if "algorithm-engineer" in intros:
        print("role_intros.json: 已存在，跳过")
        return

    intros["algorithm-engineer"] = {
        "intro": (
            "算法工程师是大厂最核心的技术岗位之一，负责推荐、搜索、风控、异常检测等系统的算法设计与优化。"
            "与机器学习工程师相比，算法工程师更偏研究导向，要求扎实数学基础（线性代数/概率统计/最优化）、"
            "论文阅读能力，以及在特定垂直领域的深厚积累。竞争激烈，顶会论文或 Kaggle 竞赛成绩可显著提升竞争力。"
        ),
        "brief": "深耕推荐/搜索/风控/异常检测，算法研究与工程落地并重的高门槛研发岗位。"
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(intros, f, ensure_ascii=False, indent=2)
    print("role_intros.json: 已添加算法工程师介绍")


def update_roadmap_skills():
    path = DATA / "roadmap_skills.json"
    with open(path, encoding="utf-8") as f:
        roadmap = json.load(f)

    if "algorithm-engineer" in roadmap:
        print("roadmap_skills.json: 已存在，跳过")
        return

    ml = roadmap.get("machine-learning", {})
    roadmap["algorithm-engineer"] = {
        "label": "算法工程师",
        "skills": ml.get("skills", []),
        "skills_zh": ml.get("skills_zh", []),
        "skill_count": ml.get("skill_count", 0),
        "related_roles": ["machine-learning", "ai-data-scientist", "ml-architect"],
        "topics": ml.get("topics", []),
        "source_roadmap": "machine-learning"
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(roadmap, f, ensure_ascii=False, indent=2)
    print("roadmap_skills.json: 已添加（复用 machine-learning 路线图）")


if __name__ == "__main__":
    update_graph_json()
    update_role_intros()
    update_roadmap_skills()
    print()
    print("=== 节点关键字段 ===")
    print(f"node_id:              algorithm-engineer")
    print(f"label:                算法工程师")
    print(f"zone:                 thrive")
    print(f"replacement_pressure: 29.0  (O*NET 15-2051.00 + AEI校准，低于ML工程师34.0)")
    print(f"salary_p50:           40000 (智联招聘算法方向中位数)")
    print(f"onet_codes:           15-2051.00 (onet_cn_index.json确认)")
    print(f"must_skills:          Python, 机器学习, PyTorch, 数学基础, Scikit-learn, SQL")
    print(f"career_level:         3 | entry_barrier: very_high")
    print(f"edges:                6条 (ML工程师/AI数据科学家/AI工程师/ML架构师)")
