"""
Regenerate graph edges for 34 CS roles using career domain knowledge.

Edge types:
  - related: natural career transition (bidirectional implication)
  - supplementary: helpful adjacent skill (weaker connection)
  - promotion: career advancement path (directional, already generated separately)

Criteria for edges:
  1. Same technology family (e.g., C++ ↔ Rust — both systems languages)
  2. Common career transitions (e.g., frontend → full-stack)
  3. Skill prerequisite chains (e.g., Docker → Kubernetes → DevOps)
  4. Specialization → generalization (e.g., React → frontend)
"""
import json
from pathlib import Path

GRAPH_PATH = Path(__file__).resolve().parent.parent / "data" / "graph.json"

# ── Hand-curated edges based on career domain knowledge ──────────────────

RELATED_EDGES = [
    # ── Software Development core transitions ──
    ("backend", "frontend", "中", "前后端互转"),
    ("backend", "full-stack", "低", "后端拓展全栈"),
    ("backend", "devops", "中", "后端转运维方向"),
    ("backend", "data-engineer", "中", "后端转数据工程"),
    ("backend", "software-architect", "高", "后端晋升架构"),
    ("backend", "java", "低", "Java 是主流后端语言"),
    ("backend", "golang", "低", "Go 是云原生后端首选"),
    ("backend", "python", "低", "Python 后端开发"),
    ("backend", "nodejs", "低", "Node.js 后端"),
    ("backend", "cpp", "中", "C++ 高性能后端"),
    ("backend", "postgresql-dba", "中", "后端深入数据库"),

    ("frontend", "full-stack", "中", "前端拓展全栈"),
    ("frontend", "react", "低", "React 是前端主流框架"),
    ("frontend", "vue", "低", "Vue 是前端主流框架"),
    ("frontend", "angular", "低", "Angular 是前端框架"),
    ("frontend", "nodejs", "低", "前端延伸到 Node"),
    ("frontend", "flutter", "中", "前端转跨端"),
    ("frontend", "react-native", "中", "前端转移动端"),

    ("full-stack", "software-architect", "高", "全栈晋升架构"),
    ("full-stack", "engineering-manager", "高", "全栈转管理"),
    ("full-stack", "devops", "中", "全栈了解运维"),

    # ── Mobile ──
    ("android", "kotlin", "低", "Kotlin 是 Android 首选语言"),
    ("android", "flutter", "中", "原生转跨端"),
    ("android", "ios", "中", "移动端互转"),
    ("android", "react-native", "中", "原生转跨端"),
    ("android", "java", "低", "Java 传统 Android 语言"),

    ("ios", "flutter", "中", "原生转跨端"),
    ("ios", "react-native", "中", "原生转跨端"),

    ("flutter", "react-native", "低", "跨端框架互转"),

    # ── Systems programming ──
    ("cpp", "rust", "中", "同为系统级语言"),
    ("cpp", "game-developer", "低", "C++ 是游戏引擎核心"),
    ("cpp", "linux", "中", "C++ 底层依赖 Linux"),
    ("cpp", "cyber-security", "中", "安全需要底层语言"),
    ("cpp", "backend", "中", "C++ 高性能服务端"),
    ("cpp", "software-architect", "高", "深入架构设计"),

    ("rust", "backend", "中", "Rust 现代后端"),
    ("rust", "devops", "中", "Rust 系统工具"),
    ("rust", "golang", "中", "同为现代系统语言"),
    ("rust", "cyber-security", "中", "安全领域 Rust 增长"),

    # ── Language generalization ──
    ("java", "kotlin", "低", "JVM 生态互通"),
    ("java", "backend", "低", "Java 企业后端主力"),
    ("java", "golang", "中", "后端语言切换"),
    ("java", "software-architect", "高", "Java 架构师路线"),

    ("python", "data-analyst", "低", "Python 数据分析"),
    ("python", "data-engineer", "中", "Python 数据工程"),
    ("python", "ai-engineer", "中", "Python 是 AI 首选"),
    ("python", "machine-learning", "中", "Python ML 开发"),
    ("python", "backend", "低", "Python Web 后端"),
    ("python", "devops", "中", "Python 自动化运维"),

    ("golang", "devops", "中", "Go 云原生工具链"),
    ("golang", "kubernetes", "中", "K8s 生态用 Go"),
    ("golang", "backend", "低", "Go 后端服务"),
    ("golang", "docker", "中", "Docker 生态用 Go"),

    ("php", "backend", "中", "PHP Web 后端"),
    ("php", "nodejs", "中", "PHP 转现代后端"),
    ("php", "vue", "低", "Laravel + Vue 常见搭配"),

    ("nodejs", "full-stack", "中", "Node 拓展全栈"),
    ("nodejs", "react", "低", "React + Node 常见搭配"),
    ("nodejs", "docker", "中", "Node 容器化部署"),

    # ── Frontend frameworks ──
    ("react", "react-native", "低", "React 延伸到移动端"),
    ("react", "vue", "低", "前端框架互转"),
    ("react", "angular", "中", "前端框架互转"),
    ("react", "nodejs", "低", "React + Node 全栈"),
    ("vue", "angular", "中", "前端框架互转"),
    ("vue", "nodejs", "低", "Vue + Node 全栈"),
    ("angular", "nodejs", "低", "Angular + Node 全栈"),

    # ── DevOps / Infra ──
    ("devops", "docker", "低", "容器是 DevOps 基础"),
    ("devops", "kubernetes", "中", "编排是 DevOps 进阶"),
    ("devops", "linux", "低", "Linux 是运维基础"),
    ("devops", "devsecops", "中", "DevOps 加安全"),
    ("devops", "software-architect", "高", "运维晋升架构"),
    ("devops", "python", "低", "Python 运维自动化"),

    ("docker", "kubernetes", "中", "容器到编排"),
    ("docker", "linux", "低", "容器依赖 Linux"),
    ("docker", "devsecops", "中", "容器安全"),

    ("kubernetes", "linux", "中", "K8s 依赖 Linux"),
    ("kubernetes", "devsecops", "中", "K8s 安全"),

    ("linux", "cyber-security", "中", "安全依赖 Linux"),
    ("linux", "backend", "中", "Linux 服务器运维"),

    ("cyber-security", "devsecops", "低", "安全运维一体化"),

    # ── AI / Data ──
    ("ai-engineer", "machine-learning", "低", "AI 和 ML 高度重叠"),
    ("ai-engineer", "mlops", "中", "AI 模型工程化"),
    ("ai-engineer", "data-engineer", "中", "AI 依赖数据工程"),
    ("ai-engineer", "software-architect", "高", "AI 架构师方向"),

    ("machine-learning", "mlops", "中", "ML 模型部署"),
    ("machine-learning", "data-engineer", "中", "ML 依赖数据"),
    ("machine-learning", "data-analyst", "中", "分析转 ML"),

    ("mlops", "devops", "中", "MLOps 和 DevOps 类似"),

    ("data-engineer", "data-analyst", "中", "数据工程和分析"),
    ("data-engineer", "postgresql-dba", "中", "数据工程依赖数据库"),

    ("data-analyst", "postgresql-dba", "中", "分析依赖 SQL"),

    # ── QA ──
    ("qa", "devops", "中", "测试转 DevOps"),
    ("qa", "devsecops", "中", "测试转安全"),
    ("qa", "frontend", "中", "前端测试"),
    ("qa", "backend", "中", "后端测试"),

    # ── Management ──
    ("software-architect", "engineering-manager", "中", "架构转管理"),
    ("engineering-manager", "software-architect", "中", "管理转架构"),

    # ── Game ──
    ("game-developer", "frontend", "中", "游戏 UI/交互"),
    ("game-developer", "ai-engineer", "高", "游戏 AI"),
]


def main():
    raw = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    node_ids = {n["node_id"] for n in raw["nodes"]}

    # Keep only promotion edges from existing data
    promotion_edges = [e for e in raw["edges"] if e.get("edge_type") == "promotion"]

    # Build new edge list
    new_edges = []
    seen = set()

    for src, tgt, diff, reason in RELATED_EDGES:
        if src not in node_ids or tgt not in node_ids:
            print(f"  SKIP: {src} -> {tgt} (node missing)")
            continue
        key = tuple(sorted([src, tgt]))
        if key in seen:
            continue
        seen.add(key)
        new_edges.append({
            "source": src,
            "target": tgt,
            "edge_type": "related",
            "difficulty": diff,
            "reason": reason,
        })

    # Re-add promotion edges
    for e in promotion_edges:
        key = (e["source"], e["target"])
        new_edges.append(e)

    raw["edges"] = new_edges
    GRAPH_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    from collections import Counter
    types = Counter(e["edge_type"] for e in new_edges)
    print(f"Done: {len(new_edges)} edges total ({dict(types)})")

    # Verify: every node has at least one edge
    connected = set()
    for e in new_edges:
        connected.add(e["source"])
        connected.add(e["target"])
    isolated = node_ids - connected
    if isolated:
        print(f"WARNING: isolated nodes: {isolated}")
    else:
        print("All 34 nodes connected.")


if __name__ == "__main__":
    main()
