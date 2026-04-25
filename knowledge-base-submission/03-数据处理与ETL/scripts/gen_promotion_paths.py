"""
Generate promotion_path (L1-L5 career ladder) for each graph node
and add promotion edges between naturally connected levels.
"""
import json
from pathlib import Path

GRAPH_PATH = Path(__file__).resolve().parent.parent / "data" / "graph.json"

# ── Per-node promotion ladder ────────────────────────────────────────────────
# Each node gets its own L1-L5 labels showing the vertical progression
# within that specialization track.

PROMOTION_PATHS: dict[str, list[dict]] = {
    # ── Software Development ──
    "backend": [
        {"level": 1, "title": "初级后端工程师"},
        {"level": 2, "title": "后端工程师"},
        {"level": 3, "title": "高级后端工程师"},
        {"level": 4, "title": "后端技术专家"},
        {"level": 5, "title": "后端架构师"},
    ],
    "frontend": [
        {"level": 1, "title": "初级前端工程师"},
        {"level": 2, "title": "前端工程师"},
        {"level": 3, "title": "高级前端工程师"},
        {"level": 4, "title": "前端技术专家"},
        {"level": 5, "title": "前端架构师"},
    ],
    "full-stack": [
        {"level": 1, "title": "初级全栈工程师"},
        {"level": 2, "title": "全栈工程师"},
        {"level": 3, "title": "高级全栈工程师"},
        {"level": 4, "title": "资深全栈工程师"},
        {"level": 5, "title": "技术合伙人"},
    ],
    "android": [
        {"level": 1, "title": "初级 Android 工程师"},
        {"level": 2, "title": "Android 工程师"},
        {"level": 3, "title": "高级 Android 工程师"},
        {"level": 4, "title": "Android 技术专家"},
        {"level": 5, "title": "移动端架构师"},
    ],
    "ios": [
        {"level": 1, "title": "初级 iOS 工程师"},
        {"level": 2, "title": "iOS 工程师"},
        {"level": 3, "title": "高级 iOS 工程师"},
        {"level": 4, "title": "iOS 技术专家"},
        {"level": 5, "title": "移动端架构师"},
    ],
    "flutter": [
        {"level": 1, "title": "初级 Flutter 工程师"},
        {"level": 2, "title": "Flutter 工程师"},
        {"level": 3, "title": "高级 Flutter 工程师"},
        {"level": 4, "title": "跨端技术专家"},
        {"level": 5, "title": "移动端架构师"},
    ],
    "react-native": [
        {"level": 1, "title": "初级 RN 工程师"},
        {"level": 2, "title": "React Native 工程师"},
        {"level": 3, "title": "高级 RN 工程师"},
        {"level": 4, "title": "跨端技术专家"},
        {"level": 5, "title": "移动端架构师"},
    ],
    "game-developer": [
        {"level": 1, "title": "初级游戏开发"},
        {"level": 2, "title": "游戏开发工程师"},
        {"level": 3, "title": "高级游戏开发"},
        {"level": 4, "title": "游戏引擎专家"},
        {"level": 5, "title": "游戏技术总监"},
    ],
    "cpp": [
        {"level": 1, "title": "初级 C++ 工程师"},
        {"level": 2, "title": "C++ 工程师"},
        {"level": 3, "title": "高级 C++ 工程师"},
        {"level": 4, "title": "C++ 技术专家"},
        {"level": 5, "title": "系统架构师"},
    ],
    "rust": [
        {"level": 1, "title": "初级 Rust 工程师"},
        {"level": 2, "title": "Rust 工程师"},
        {"level": 3, "title": "高级 Rust 工程师"},
        {"level": 4, "title": "Rust 技术专家"},
        {"level": 5, "title": "系统架构师"},
    ],
    "python": [
        {"level": 1, "title": "初级 Python 工程师"},
        {"level": 2, "title": "Python 工程师"},
        {"level": 3, "title": "高级 Python 工程师"},
        {"level": 4, "title": "Python 技术专家"},
        {"level": 5, "title": "技术架构师"},
    ],
    "java": [
        {"level": 1, "title": "初级 Java 工程师"},
        {"level": 2, "title": "Java 工程师"},
        {"level": 3, "title": "高级 Java 工程师"},
        {"level": 4, "title": "Java 技术专家"},
        {"level": 5, "title": "Java 架构师"},
    ],
    "golang": [
        {"level": 1, "title": "初级 Go 工程师"},
        {"level": 2, "title": "Go 工程师"},
        {"level": 3, "title": "高级 Go 工程师"},
        {"level": 4, "title": "Go 技术专家"},
        {"level": 5, "title": "后端架构师"},
    ],
    "kotlin": [
        {"level": 1, "title": "初级 Kotlin 工程师"},
        {"level": 2, "title": "Kotlin 工程师"},
        {"level": 3, "title": "高级 Kotlin 工程师"},
        {"level": 4, "title": "Kotlin 技术专家"},
        {"level": 5, "title": "移动端架构师"},
    ],
    "php": [
        {"level": 1, "title": "初级 PHP 工程师"},
        {"level": 2, "title": "PHP 工程师"},
        {"level": 3, "title": "高级 PHP 工程师"},
        {"level": 4, "title": "PHP 技术专家"},
        {"level": 5, "title": "Web 架构师"},
    ],
    "react": [
        {"level": 1, "title": "初级 React 工程师"},
        {"level": 2, "title": "React 工程师"},
        {"level": 3, "title": "高级 React 工程师"},
        {"level": 4, "title": "React 技术专家"},
        {"level": 5, "title": "前端架构师"},
    ],
    "vue": [
        {"level": 1, "title": "初级 Vue 工程师"},
        {"level": 2, "title": "Vue 工程师"},
        {"level": 3, "title": "高级 Vue 工程师"},
        {"level": 4, "title": "Vue 技术专家"},
        {"level": 5, "title": "前端架构师"},
    ],
    "angular": [
        {"level": 1, "title": "初级 Angular 工程师"},
        {"level": 2, "title": "Angular 工程师"},
        {"level": 3, "title": "高级 Angular 工程师"},
        {"level": 4, "title": "Angular 技术专家"},
        {"level": 5, "title": "前端架构师"},
    ],
    "nodejs": [
        {"level": 1, "title": "初级 Node.js 工程师"},
        {"level": 2, "title": "Node.js 工程师"},
        {"level": 3, "title": "高级 Node.js 工程师"},
        {"level": 4, "title": "Node.js 技术专家"},
        {"level": 5, "title": "全栈架构师"},
    ],
    # ── Algorithm / AI ──
    "ai-engineer": [
        {"level": 1, "title": "初级 AI 工程师"},
        {"level": 2, "title": "AI 工程师"},
        {"level": 3, "title": "高级 AI 工程师"},
        {"level": 4, "title": "AI 技术专家"},
        {"level": 5, "title": "AI 首席科学家"},
    ],
    "machine-learning": [
        {"level": 1, "title": "初级 ML 工程师"},
        {"level": 2, "title": "机器学习工程师"},
        {"level": 3, "title": "高级 ML 工程师"},
        {"level": 4, "title": "ML 技术专家"},
        {"level": 5, "title": "算法架构师"},
    ],
    "mlops": [
        {"level": 1, "title": "初级 MLOps 工程师"},
        {"level": 2, "title": "MLOps 工程师"},
        {"level": 3, "title": "高级 MLOps 工程师"},
        {"level": 4, "title": "MLOps 技术专家"},
        {"level": 5, "title": "AI 平台架构师"},
    ],
    # ── Data ──
    "data-engineer": [
        {"level": 1, "title": "初级数据工程师"},
        {"level": 2, "title": "数据工程师"},
        {"level": 3, "title": "高级数据工程师"},
        {"level": 4, "title": "数据平台专家"},
        {"level": 5, "title": "数据架构师"},
    ],
    "data-analyst": [
        {"level": 1, "title": "初级数据分析师"},
        {"level": 2, "title": "数据分析师"},
        {"level": 3, "title": "高级数据分析师"},
        {"level": 4, "title": "数据分析专家"},
        {"level": 5, "title": "数据科学总监"},
    ],
    "postgresql-dba": [
        {"level": 1, "title": "初级数据库工程师"},
        {"level": 2, "title": "数据库工程师"},
        {"level": 3, "title": "高级数据库工程师"},
        {"level": 4, "title": "数据库专家"},
        {"level": 5, "title": "数据库架构师"},
    ],
    # ── DevOps / Infra ──
    "devops": [
        {"level": 1, "title": "初级运维工程师"},
        {"level": 2, "title": "DevOps 工程师"},
        {"level": 3, "title": "高级 DevOps 工程师"},
        {"level": 4, "title": "DevOps 技术专家"},
        {"level": 5, "title": "基础设施架构师"},
    ],
    "cyber-security": [
        {"level": 1, "title": "初级安全工程师"},
        {"level": 2, "title": "网络安全工程师"},
        {"level": 3, "title": "高级安全工程师"},
        {"level": 4, "title": "安全技术专家"},
        {"level": 5, "title": "首席安全官"},
    ],
    "devsecops": [
        {"level": 1, "title": "初级 DevSecOps 工程师"},
        {"level": 2, "title": "DevSecOps 工程师"},
        {"level": 3, "title": "高级 DevSecOps 工程师"},
        {"level": 4, "title": "DevSecOps 技术专家"},
        {"level": 5, "title": "安全架构师"},
    ],
    "kubernetes": [
        {"level": 1, "title": "初级 K8s 工程师"},
        {"level": 2, "title": "Kubernetes 工程师"},
        {"level": 3, "title": "高级 K8s 工程师"},
        {"level": 4, "title": "云原生技术专家"},
        {"level": 5, "title": "云原生架构师"},
    ],
    "linux": [
        {"level": 1, "title": "初级 Linux 运维"},
        {"level": 2, "title": "Linux 工程师"},
        {"level": 3, "title": "高级 Linux 工程师"},
        {"level": 4, "title": "系统工程专家"},
        {"level": 5, "title": "基础设施架构师"},
    ],
    "docker": [
        {"level": 1, "title": "初级容器工程师"},
        {"level": 2, "title": "Docker 工程师"},
        {"level": 3, "title": "高级容器工程师"},
        {"level": 4, "title": "容器化技术专家"},
        {"level": 5, "title": "云原生架构师"},
    ],
    # ── QA ──
    "qa": [
        {"level": 1, "title": "初级测试工程师"},
        {"level": 2, "title": "测试工程师"},
        {"level": 3, "title": "高级测试工程师"},
        {"level": 4, "title": "测试架构师"},
        {"level": 5, "title": "质量总监"},
    ],
    # ── Management (already L5) ──
    "software-architect": [
        {"level": 1, "title": "初级开发工程师"},
        {"level": 2, "title": "开发工程师"},
        {"level": 3, "title": "高级工程师"},
        {"level": 4, "title": "技术专家"},
        {"level": 5, "title": "软件架构师"},
    ],
    "engineering-manager": [
        {"level": 1, "title": "初级工程师"},
        {"level": 2, "title": "工程师"},
        {"level": 3, "title": "高级工程师 / Tech Lead"},
        {"level": 4, "title": "技术经理"},
        {"level": 5, "title": "工程总监"},
    ],
}

# ── Promotion edges ──────────────────────────────────────────────────────────
# Natural career progression between existing nodes at different levels.
# Format: (source_id, target_id, difficulty, gap_skills, reason)

PROMOTION_EDGES = [
    # L2 → L3 (within same family)
    ("frontend", "full-stack", "中", ["Node.js", "PostgreSQL", "Docker"], "前端深入后拓展全栈能力"),
    ("frontend", "backend", "高", ["Java/Go", "MySQL", "系统设计"], "前端转后端需要较大技能跨越"),
    ("android", "flutter", "低", ["Dart", "跨端架构"], "原生转跨端门槛较低"),
    ("ios", "flutter", "低", ["Dart", "跨端架构"], "原生转跨端门槛较低"),
    ("python", "backend", "中", ["系统设计", "数据库优化", "高并发"], "语言工程师升级为后端工程师"),
    ("python", "data-engineer", "中", ["Spark", "数据建模", "ETL"], "Python 转数据工程"),
    ("java", "backend", "低", ["系统架构", "微服务", "性能调优"], "Java 工程师自然升级"),
    ("react", "frontend", "低", ["跨框架能力", "工程化"], "框架工程师升级为前端工程师"),
    ("vue", "frontend", "低", ["跨框架能力", "工程化"], "框架工程师升级为前端工程师"),
    ("angular", "frontend", "中", ["React/Vue", "工程化"], "Angular 转通用前端"),
    ("nodejs", "full-stack", "中", ["React/Vue", "数据库设计"], "Node.js 拓展为全栈"),
    ("linux", "devops", "中", ["Docker", "CI/CD", "Terraform"], "运维升级为 DevOps"),
    ("docker", "kubernetes", "中", ["K8s 编排", "Helm", "服务网格"], "容器化升级为编排"),
    ("docker", "devops", "中", ["CI/CD", "Terraform", "监控"], "容器工程师转 DevOps"),
    ("data-analyst", "data-engineer", "中", ["Spark", "ETL", "数据建模"], "分析师转数据工程"),
    ("qa", "devsecops", "中", ["安全测试", "CI/CD", "容器安全"], "测试转安全方向"),
    ("kotlin", "android", "低", ["Android SDK", "Jetpack Compose"], "Kotlin 转 Android"),
    ("php", "backend", "高", ["Java/Go", "微服务", "系统设计"], "PHP 转现代后端栈"),
    ("golang", "backend", "低", ["系统架构", "微服务"], "Go 工程师升级为后端工程师"),

    # L3 → L5 (senior → architect/manager)
    ("backend", "software-architect", "高", ["架构设计", "技术战略", "团队影响力"], "后端高工晋升架构师"),
    ("full-stack", "software-architect", "高", ["架构设计", "技术决策", "技术影响力"], "全栈高工晋升架构师"),
    ("backend", "engineering-manager", "高", ["团队管理", "项目管理", "业务理解"], "后端高工转管理线"),
    ("full-stack", "engineering-manager", "高", ["团队管理", "项目管理", "业务理解"], "全栈高工转管理线"),
    ("devops", "software-architect", "高", ["系统架构", "技术战略"], "DevOps 晋升架构师"),
    ("ai-engineer", "software-architect", "高", ["系统架构", "技术战略", "跨团队协调"], "AI 高工晋升架构师"),
    ("machine-learning", "software-architect", "高", ["系统架构", "工程化能力"], "ML 高工晋升架构师"),
    ("data-engineer", "software-architect", "高", ["系统架构", "技术决策"], "数据高工晋升架构师"),
    ("cyber-security", "engineering-manager", "高", ["团队管理", "安全战略", "合规"], "安全高工转管理线"),
]


def main():
    raw = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))

    # 1. Add promotion_path to each node
    nid_set = {n["node_id"] for n in raw["nodes"]}
    for node in raw["nodes"]:
        nid = node["node_id"]
        path = PROMOTION_PATHS.get(nid)
        if path:
            node["promotion_path"] = path
        else:
            print(f"  WARNING: no promotion_path for {nid}")

    # 2. Add promotion edges (avoid duplicates)
    existing = {(e["source"], e["target"]) for e in raw["edges"]}
    added = 0
    for src, tgt, diff, gap, reason in PROMOTION_EDGES:
        if src not in nid_set or tgt not in nid_set:
            print(f"  SKIP: {src} -> {tgt} (node missing)")
            continue
        if (src, tgt) in existing:
            # Update existing edge to also be promotion type? No, add new one.
            continue
        raw["edges"].append({
            "source": src,
            "target": tgt,
            "edge_type": "promotion",
            "difficulty": diff,
            "gap_skills": gap,
            "reason": reason,
        })
        added += 1

    GRAPH_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Done: promotion_path for {len(raw['nodes'])} nodes, {added} new promotion edges")


if __name__ == "__main__":
    main()
