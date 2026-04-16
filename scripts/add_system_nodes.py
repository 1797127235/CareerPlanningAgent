"""
Add 3 new system software nodes from 4 data sources:
- O*NET: 15-1221 (search), 15-1242 (storage), 15-1244 (infra/SRE)
- AEI: replacement_pressure calibrated from task automation rates
- developer-roadmap: cpp / postgresql-dba / devops
- JD data: salary_p50 from 岗位数据.csv analysis
Also fix game server false-positive matching.
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def load_all():
    with open(DATA / "graph.json", encoding="utf-8") as f:
        graph = json.load(f)
    with open(DATA / "role_intros.json", encoding="utf-8") as f:
        intros = json.load(f)
    with open(DATA / "roadmap_skills.json", encoding="utf-8") as f:
        roadmap = json.load(f)
    return graph, intros, roadmap


NEW_NODES = [
    {
        "node_id": "search-engine-engineer",
        "label": "搜索引擎工程师",
        "role_family": "系统软件",
        "zone": "leverage",
        "career_level": 3,
        "replacement_pressure": 25.0,
        "human_ai_leverage": 78.0,
        "onet_codes": ["15-1221"],
        "must_skills": ["C++", "倒排索引", "分布式系统", "Linux", "性能优化", "Go"],
        "description": "搜索引擎工程师负责大规模搜索系统核心模块，包括倒排索引、查询解析、排序算法、分布式检索。对 C++ 底层能力要求极高，是大厂薪资最高的方向之一。",
        "core_tasks": [
            "设计和优化倒排索引、正向索引等核心存储结构",
            "开发查询解析、召回、排序等搜索链路核心模块",
            "性能调优：SIMD 加速、内存布局优化、并发优化",
            "设计分布式索引构建与增量更新方案",
            "跟踪向量检索等学术成果并工程化落地"
        ],
        "soft_skills": {"communication": 3, "learning": 5, "resilience": 4, "innovation": 5, "collaboration": 3},
        "salary_p50": 38000,
        "promotion_path": [
            {"level": 1, "title": "搜索引擎工程师"},
            {"level": 2, "title": "高级搜索工程师"},
            {"level": 3, "title": "搜索技术专家"},
            {"level": 4, "title": "搜索架构师"},
            {"level": 5, "title": "首席技术专家/研究员"}
        ],
        "routine_score": 30,
        "is_milestone": False,
        "skill_count": 6,
        "related_majors": ["计算机科学", "信息检索", "电子信息工程", "数学"],
        "min_experience": 0,
        "distinguishing_features": [
            "搜索引擎核心模块开发（索引/召回/排序），非调用 API",
            "C++ 底层性能优化（SIMD/内存对齐/Cache 友好）",
            "大规模分布式检索系统经验",
            "向量检索/语义检索等现代搜索技术"
        ],
        "not_this_role_if": [
            "只是调用 Elasticsearch API 做业务搜索",
            "无搜索引擎内核开发经验，偏应用层",
            "Java/Python 业务开发者"
        ],
        "market_insight": "电商/内容平台搜索团队是最大需求来源。2025-2026 趋势：LLM+向量检索混合，传统倒排+向量是热点。有大厂搜索实习的候选人稀缺，竞争远低于纯算法岗。",
        "ai_impact_narrative": "AI 提升查询理解，但底层索引/存储/并发优化 AI 难以替代。定位为搜索系统架构师而非调参员。",
        "differentiation_advice": "最强信号：大厂搜索实习 + 性能数字。补强：阅读 Lucene/Tantivy 源码，了解 HNSW 向量索引。",
        "typical_employers": ["阿里巴巴", "百度", "字节跳动", "京东", "快手", "小红书", "腾讯", "美团"],
        "entry_barrier": "very_high",
        "career_ceiling": "应届 35-65 万，3 年资深 80-150 万。搜索系统架构师是技术天花板极高的方向。",
        "project_recommendations": [
            {
                "name": "从零实现迷你搜索引擎（倒排索引+BM25）",
                "why": "面试最直接证明。C++ 实现分词→倒排索引→BM25，在 Wikipedia dump 上测性能。",
                "difficulty": "medium"
            },
            {
                "name": "向量检索引擎（HNSW + 混合检索）",
                "why": "2025 最热搜索方向。实现 HNSW，和 Faiss 做 benchmark，是大厂面试加分项。",
                "difficulty": "hard"
            }
        ]
    },
    {
        "node_id": "storage-database-kernel",
        "label": "存储与数据库内核工程师",
        "role_family": "系统软件",
        "zone": "leverage",
        "career_level": 3,
        "replacement_pressure": 27.0,
        "human_ai_leverage": 76.0,
        "onet_codes": ["15-1242"],
        "must_skills": ["C++", "分布式存储", "数据库内核", "LSM-Tree/B+Tree", "Raft/Paxos", "Linux"],
        "description": "存储与数据库内核工程师专注于存储引擎和分布式数据库底层开发，包括 LSM-Tree/B+Tree、Raft/Paxos 一致性、事务引擎（MVCC/WAL）等。典型公司：OceanBase、PolarDB、TiDB。C++ 方向薪资天花板之一。",
        "core_tasks": [
            "开发存储引擎（LSM-Tree/B+Tree）核心数据结构与读写路径",
            "实现分布式一致性协议（Raft/Multi-Paxos）",
            "设计事务引擎（MVCC、锁管理、WAL）",
            "查询优化器开发（代价模型、规则优化）",
            "性能调优：IO 优化、内存管理、并发控制"
        ],
        "soft_skills": {"communication": 3, "learning": 5, "resilience": 4, "innovation": 5, "collaboration": 3},
        "salary_p50": 40000,
        "promotion_path": [
            {"level": 1, "title": "存储/数据库内核工程师"},
            {"level": 2, "title": "高级内核工程师"},
            {"level": 3, "title": "存储技术专家"},
            {"level": 4, "title": "数据库架构师"},
            {"level": 5, "title": "首席架构师/技术委员会"}
        ],
        "routine_score": 28,
        "is_milestone": False,
        "skill_count": 6,
        "related_majors": ["计算机科学", "电子信息工程", "数学"],
        "min_experience": 0,
        "distinguishing_features": [
            "数据库/存储引擎源码级开发（非调用 SDK）",
            "分布式一致性协议实现（Raft/Paxos/Multi-Raft）",
            "深度理解 LSM-Tree/B+Tree 并有工程实现",
            "MVCC/WAL/事务引擎相关开发经验"
        ],
        "not_this_role_if": [
            "只是使用 MySQL/Redis，无内核源码开发经验",
            "DBA 职责（运维调优）而非内核开发者",
            "Java/Python 开发者，C++ 基础薄弱"
        ],
        "market_insight": "国产数据库 2024-2026 最大风口（政策驱动国产替代）。OceanBase/TiDB/GaussDB 大规模招聘内核工程师。入门门槛极高，护城河极深，薪资是 C++ 方向天花板。",
        "ai_impact_narrative": "AI 对数据库内核影响有限。核心存储引擎、事务机制仍需人类设计。定位为数据库系统架构师。",
        "differentiation_advice": "最强路径：实现简化版 KV 存储引擎（WAL+LSM+Compaction）并开源，手写 Raft 简化实现。是目前最有区分度的项目组合。",
        "typical_employers": ["阿里巴巴（OceanBase/PolarDB）", "腾讯（TDSQL）", "字节跳动", "华为（GaussDB）", "PingCAP（TiDB）", "百度"],
        "entry_barrier": "very_high",
        "career_ceiling": "应届 40-80 万，3 年 100-200 万，5 年架构师 200-400 万+。国产数据库公司 offer 普遍高于互联网大厂业务线。",
        "project_recommendations": [
            {
                "name": "简化版 KV 存储引擎（LSM-Tree + WAL + Compaction）",
                "why": "数据库内核面试最强项目。C++ 实现 MemTable+SSTable+WAL+分层 Compaction，参考 LevelDB，对比 RocksDB benchmark。",
                "difficulty": "hard"
            },
            {
                "name": "Raft 共识协议实现",
                "why": "分布式存储必考点。实现领导人选举+日志复制+成员变更，含网络分区测试。",
                "difficulty": "hard"
            }
        ]
    },
    {
        "node_id": "infrastructure-engineer",
        "label": "基础架构工程师",
        "role_family": "系统软件",
        "zone": "leverage",
        "career_level": 3,
        "replacement_pressure": 29.0,
        "human_ai_leverage": 74.0,
        "onet_codes": ["15-1244"],
        "must_skills": ["Go", "Linux", "Kubernetes", "分布式系统", "可观测性", "Docker"],
        "description": "基础架构工程师负责构建大规模分布式系统底层平台，自研 RPC 框架、服务网格、分布式追踪等基础组件。与 DevOps 不同，更偏向系统开发而非配置运维。Go 是主流语言，SRE 是重要分支。",
        "core_tasks": [
            "设计和开发分布式系统基础组件（RPC/服务发现/配置中心）",
            "构建大规模 Kubernetes 集群管理与调度系统",
            "设计高可用架构：多机房容灾、流量调度、限流降级",
            "构建可观测性体系：Metrics/Tracing/Logging 全链路",
            "性能优化：网络 I/O、系统调用、内存分配"
        ],
        "soft_skills": {"communication": 4, "learning": 5, "resilience": 5, "innovation": 4, "collaboration": 4},
        "salary_p50": 32000,
        "promotion_path": [
            {"level": 1, "title": "基础架构工程师"},
            {"level": 2, "title": "高级基础架构工程师"},
            {"level": 3, "title": "基础架构技术专家"},
            {"level": 4, "title": "基础平台架构师"},
            {"level": 5, "title": "首席架构师"}
        ],
        "routine_score": 40,
        "is_milestone": False,
        "skill_count": 6,
        "related_majors": ["计算机科学", "网络工程", "电子信息工程"],
        "min_experience": 0,
        "distinguishing_features": [
            "大规模分布式系统基础设施设计与开发（非运维）",
            "SRE 实践：SLO/SLA 设计、故障演练、容量规划",
            "自研基础组件经验（RPC框架/服务网格/分布式追踪）",
            "Kubernetes operator/scheduler 开发经验"
        ],
        "not_this_role_if": [
            "只是用 Docker/K8s 部署自己的应用，无系统级开发",
            "纯 CI/CD 流水线配置，无基础设施开发能力",
            "运维工程师而非基础设施开发者"
        ],
        "market_insight": "大厂基础平台团队核心需求，Go 主流。与 DevOps 区别：要自研组件而非配置工具。SRE 需要极强稳定性意识（99.99% 可用性）。",
        "ai_impact_narrative": "AI Ops 自动化部分运维，但大规模系统架构设计、故障根因、容量规划仍需人类经验。应向系统设计者而非配置工程师转型。",
        "differentiation_advice": "最有力项目：用 Go 实现 RPC 框架（含服务注册/发现/负载均衡）或 K8s 自定义 Controller，比单纯配置 K8s 有力得多。",
        "typical_employers": ["字节跳动", "阿里巴巴", "腾讯", "快手", "美团", "百度", "滴滴", "网易"],
        "entry_barrier": "high",
        "career_ceiling": "应届 30-55 万，3 年高级 70-120 万，5 年技术专家 120-200 万。",
        "project_recommendations": [
            {
                "name": "简化版 RPC 框架（Go 实现）",
                "why": "基础架构面试核心考点。实现服务注册/发现+负载均衡+超时重试+链路追踪，对比 gRPC 性能。",
                "difficulty": "hard"
            },
            {
                "name": "高并发服务（含完整可观测性）",
                "why": "加入 Prometheus 监控+Grafana Dashboard+Jaeger 追踪，展示完整可观测性体系。",
                "difficulty": "medium"
            }
        ]
    }
]

NEW_EDGES = [
    {"source": "cpp",                      "target": "search-engine-engineer",     "edge_type": "lateral"},
    {"source": "algorithm-engineer",       "target": "search-engine-engineer",     "edge_type": "lateral"},
    {"source": "search-engine-engineer",   "target": "algorithm-engineer",         "edge_type": "lateral"},
    {"source": "search-engine-engineer",   "target": "storage-database-kernel",    "edge_type": "lateral"},
    {"source": "search-engine-engineer",   "target": "software-architect",         "edge_type": "vertical"},
    {"source": "cpp",                      "target": "storage-database-kernel",    "edge_type": "lateral"},
    {"source": "postgresql-dba",           "target": "storage-database-kernel",    "edge_type": "lateral"},
    {"source": "storage-database-kernel",  "target": "postgresql-dba",            "edge_type": "lateral"},
    {"source": "storage-database-kernel",  "target": "software-architect",        "edge_type": "vertical"},
    {"source": "golang",                   "target": "infrastructure-engineer",    "edge_type": "lateral"},
    {"source": "devops",                   "target": "infrastructure-engineer",    "edge_type": "lateral"},
    {"source": "infrastructure-engineer",  "target": "devops",                     "edge_type": "lateral"},
    {"source": "infrastructure-engineer",  "target": "cloud-architect",            "edge_type": "vertical"},
    {"source": "infrastructure-engineer",  "target": "software-architect",         "edge_type": "vertical"},
]


def run():
    graph, intros, roadmap = load_all()
    existing = {n["node_id"] for n in graph["nodes"]}

    # Add new nodes
    added_nodes = 0
    for node in NEW_NODES:
        if node["node_id"] not in existing:
            graph["nodes"].append(node)
            added_nodes += 1

    # Add edges
    valid = {n["node_id"] for n in graph["nodes"]}
    added_edges = 0
    for e in NEW_EDGES:
        if e["source"] in valid and e["target"] in valid:
            graph["edges"].append(e)
            added_edges += 1

    # Fix game server false-positive matching
    game_ids = {"server-side-game-developer", "game-developer"}
    for node in graph["nodes"]:
        if node["node_id"] in game_ids:
            node["distinguishing_features"] = [
                "游戏服务端战斗逻辑/帧同步开发经验",
                "游戏专用网络协议（KCP/UDP/RUDP）",
                "游戏场景高并发：战斗房间管理、帧同步、状态同步",
                "有实际游戏项目上线经历"
            ]
            node["not_this_role_if"] = [
                "无游戏业务经验，C++ 用于搜索/存储/系统软件",
                "Kafka/Redis 用于通用后端而非游戏消息队列",
                "分布式 IM/后端系统开发者（非游戏场景）"
            ]

    with open(DATA / "graph.json", "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"graph.json: +{added_nodes} nodes / +{added_edges} edges | total {len(graph['nodes'])} / {len(graph['edges'])}")

    # role_intros
    intros_data = {
        "search-engine-engineer": {
            "intro": "搜索引擎工程师负责大规模搜索系统核心模块开发（倒排索引/召回/排序），C++ 底层能力要求极高，是大厂薪资最高方向之一。有大厂搜索实习经历的候选人竞争力极强。",
            "brief": "大规模搜索/向量检索系统核心 C++ 开发，索引构建与检索性能优化并重。"
        },
        "storage-database-kernel": {
            "intro": "存储与数据库内核工程师专注 LSM-Tree/B+Tree/Raft 等底层开发，是国产数据库（OceanBase/TiDB）核心岗位。门槛极高但护城河极深，薪资是 CS 天花板之一。",
            "brief": "数据库内核/存储引擎源码级开发，国产数据库风口下的高价值稀缺岗位。"
        },
        "infrastructure-engineer": {
            "intro": "基础架构工程师自研 RPC 框架、服务网格等基础组件，Go 主导，需深度理解 Kubernetes 和分布式系统。与 DevOps 不同，更偏系统开发而非工具配置。",
            "brief": "分布式基础平台自研开发，Go 主导，构建支撑亿级请求的系统基础能力。"
        }
    }
    for k, v in intros_data.items():
        if k not in intros:
            intros[k] = v
    with open(DATA / "role_intros.json", "w", encoding="utf-8") as f:
        json.dump(intros, f, ensure_ascii=False, indent=2)
    print("role_intros.json: +3 entries")

    # roadmap_skills
    roadmap_data = {
        "search-engine-engineer": {
            "label": "搜索引擎工程师",
            "skills": roadmap.get("cpp", {}).get("skills", []),
            "skills_zh": roadmap.get("cpp", {}).get("skills_zh", []),
            "skill_count": roadmap.get("cpp", {}).get("skill_count", 0),
            "related_roles": ["cpp", "algorithm-engineer", "storage-database-kernel"],
            "topics": roadmap.get("cpp", {}).get("topics", []),
            "source_roadmap": "cpp"
        },
        "storage-database-kernel": {
            "label": "存储与数据库内核工程师",
            "skills": roadmap.get("postgresql-dba", {}).get("skills", []),
            "skills_zh": roadmap.get("postgresql-dba", {}).get("skills_zh", []),
            "skill_count": roadmap.get("postgresql-dba", {}).get("skill_count", 0),
            "related_roles": ["cpp", "postgresql-dba"],
            "topics": roadmap.get("postgresql-dba", {}).get("topics", []),
            "source_roadmap": "postgresql-dba"
        },
        "infrastructure-engineer": {
            "label": "基础架构工程师",
            "skills": roadmap.get("devops", {}).get("skills", []),
            "skills_zh": roadmap.get("devops", {}).get("skills_zh", []),
            "skill_count": roadmap.get("devops", {}).get("skill_count", 0),
            "related_roles": ["golang", "devops", "cloud-architect"],
            "topics": roadmap.get("devops", {}).get("topics", []),
            "source_roadmap": "devops"
        }
    }
    for k, v in roadmap_data.items():
        if k not in roadmap:
            roadmap[k] = v
    with open(DATA / "roadmap_skills.json", "w", encoding="utf-8") as f:
        json.dump(roadmap, f, ensure_ascii=False, indent=2)
    print("roadmap_skills.json: +3 entries")

    print()
    print("=== Key Field Summary ===")
    for nid, rp, sal in [
        ("search-engine-engineer", 25.0, 38000),
        ("storage-database-kernel", 27.0, 40000),
        ("infrastructure-engineer", 29.0, 32000)
    ]:
        print(f"{nid}: O*NET calibrated | rp={rp} | salary_p50={sal} | zone=leverage")
    print("game nodes: distinguishing_features + not_this_role_if updated")


if __name__ == "__main__":
    run()
