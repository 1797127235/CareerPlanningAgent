"""
Build graph.json from roadmap_skills.json.

Generates career graph nodes + edges for the 3D terrain visualization.
Metadata (zone, salary, AI scores) is manually curated for the 2026
Chinese tech market — suitable for CS students and early-career devs.

Usage:
    python -m scripts.build_roadmap_graph

Output: data/graph.json
"""

import json
from pathlib import Path

_DATA_DIR = Path("data")
_INPUT = _DATA_DIR / "roadmap_skills.json"
_OUTPUT = _DATA_DIR / "graph.json"


# ═══════════════════════════════════════════════════════════════════════════
# Role metadata — curated for 2026 Chinese tech market
# ═══════════════════════════════════════════════════════════════════════════
#
# Sources / rationale:
#   salary_p50    — monthly RMB, mid-career (3-5yr), tier-1 cities
#                   based on Maimai/Boss直聘/拉勾 2025 data, +5% YoY
#   replacement_pressure — 0-100, how automatable the ROUTINE part is
#   human_ai_leverage    — 0-100, how much AI amplifies SENIOR practitioners
#   career_level  — 1=intern/junior, 2=mid, 3=senior, 4=staff, 5=principal
#   zone          — derived: safe/leverage/transition/danger
#
# Zone derivation logic:
#   leverage  : human_ai_leverage >= 65 AND replacement_pressure < 40
#   safe      : human_ai_leverage - replacement_pressure > 25
#   danger    : replacement_pressure >= 58
#   transition: everything else

ROLE_META: dict[str, dict] = {
    # ── Core engineering ────────────────────────────────────────────────
    "backend": {
        "role_family": "software_development",
        "salary_p50": 25000, "replacement_pressure": 35, "human_ai_leverage": 68, "career_level": 3,
        "core_tasks": ["服务端开发", "API设计", "数据库优化", "系统架构", "性能调优"],
        "display_skills": ["Java", "Python", "Go", "MySQL", "Redis", "Docker"],
    },
    "frontend": {
        "role_family": "software_development",
        "salary_p50": 22000, "replacement_pressure": 48, "human_ai_leverage": 62, "career_level": 2,
        "core_tasks": ["页面开发", "组件设计", "性能优化", "跨端适配", "交互实现"],
        "display_skills": ["React", "Vue.js", "TypeScript", "CSS", "Webpack", "Next.js"],
    },
    "full-stack": {
        "role_family": "software_development",
        "salary_p50": 28000, "replacement_pressure": 32, "human_ai_leverage": 72, "career_level": 3,
        "core_tasks": ["全栈开发", "系统集成", "技术选型", "原型构建", "端到端交付"],
        "display_skills": ["React", "Node.js", "Python", "PostgreSQL", "Docker", "AWS"],
    },
    "devops": {
        "role_family": "devops_infra",
        "salary_p50": 26000, "replacement_pressure": 30, "human_ai_leverage": 70, "career_level": 3,
        "core_tasks": ["CI/CD流水线", "基础设施管理", "容器编排", "监控告警", "故障排查"],
        "display_skills": ["Docker", "Kubernetes", "Jenkins", "Terraform", "Linux", "Python"],
    },

    # ── Mobile ──────────────────────────────────────────────────────────
    "android": {
        "role_family": "software_development",
        "salary_p50": 23000, "replacement_pressure": 42, "human_ai_leverage": 58, "career_level": 2,
        "core_tasks": ["Android应用开发", "性能优化", "SDK集成", "架构设计", "发版管理"],
        "display_skills": ["Kotlin", "Java", "Jetpack", "Gradle", "SQLite", "Firebase"],
    },
    "ios": {
        "role_family": "software_development",
        "salary_p50": 25000, "replacement_pressure": 40, "human_ai_leverage": 60, "career_level": 2,
        "core_tasks": ["iOS应用开发", "Swift/ObjC开发", "UI适配", "性能调优", "审核上架"],
        "display_skills": ["Swift", "SwiftUI", "UIKit", "Xcode", "CoreData", "Combine"],
    },
    "flutter": {
        "role_family": "software_development",
        "salary_p50": 24000, "replacement_pressure": 42, "human_ai_leverage": 64, "career_level": 2,
        "core_tasks": ["跨平台移动开发", "Widget开发", "原生桥接", "性能优化", "多端适配"],
        "display_skills": ["Dart", "Flutter", "Firebase", "SQLite", "REST API", "Git"],
    },
    "react-native": {
        "role_family": "software_development",
        "salary_p50": 23000, "replacement_pressure": 44, "human_ai_leverage": 60, "career_level": 2,
        "core_tasks": ["RN应用开发", "原生模块开发", "热更新", "性能优化", "多端适配"],
        "display_skills": ["React Native", "JavaScript", "TypeScript", "Redux", "Expo", "Git"],
    },

    # ── AI / Data ───────────────────────────────────────────────────────
    "ai-engineer": {
        "role_family": "algorithm_ai",
        "salary_p50": 35000, "replacement_pressure": 15, "human_ai_leverage": 88, "career_level": 3,
        "core_tasks": ["LLM应用开发", "RAG系统构建", "Agent编排", "模型评估", "AI产品落地"],
        "display_skills": ["Python", "LLM", "RAG", "LangChain", "Vector DB", "OpenAI API"],
    },
    "machine-learning": {
        "role_family": "algorithm_ai",
        "salary_p50": 33000, "replacement_pressure": 20, "human_ai_leverage": 82, "career_level": 3,
        "core_tasks": ["模型训练", "特征工程", "数据分析", "算法优化", "模型部署"],
        "display_skills": ["Python", "PyTorch", "TensorFlow", "Pandas", "Scikit-learn", "SQL"],
    },
    "mlops": {
        "role_family": "algorithm_ai",
        "salary_p50": 30000, "replacement_pressure": 22, "human_ai_leverage": 78, "career_level": 3,
        "core_tasks": ["模型部署", "训练流水线", "模型监控", "特征存储", "AB实验"],
        "display_skills": ["Python", "Docker", "Kubernetes", "MLflow", "Airflow", "AWS"],
    },
    "data-engineer": {
        "role_family": "data_engineering",
        "salary_p50": 28000, "replacement_pressure": 28, "human_ai_leverage": 72, "career_level": 3,
        "core_tasks": ["数据管道开发", "ETL/ELT", "数据仓库建设", "实时计算", "数据治理"],
        "display_skills": ["Python", "SQL", "Spark", "Kafka", "Airflow", "Flink"],
    },
    "data-analyst": {
        "role_family": "data_analysis",
        "salary_p50": 18000, "replacement_pressure": 55, "human_ai_leverage": 65, "career_level": 2,
        "core_tasks": ["数据分析", "报表开发", "业务洞察", "AB实验分析", "数据可视化"],
        "display_skills": ["SQL", "Python", "Pandas", "Tableau", "Excel", "R"],
    },

    # ── Architecture & Management ───────────────────────────────────────
    "software-architect": {
        "role_family": "management",
        "salary_p50": 42000, "replacement_pressure": 12, "human_ai_leverage": 80, "career_level": 5,
        "core_tasks": ["系统架构设计", "技术选型", "架构评审", "技术规划", "团队指导"],
        "display_skills": ["系统设计", "微服务", "DDD", "云架构", "性能优化", "技术选型"],
    },
    "engineering-manager": {
        "role_family": "management",
        "salary_p50": 45000, "replacement_pressure": 10, "human_ai_leverage": 75, "career_level": 5,
        "core_tasks": ["团队管理", "项目规划", "技术决策", "绩效管理", "人才培养"],
        "display_skills": ["团队管理", "项目管理", "技术决策", "Agile", "OKR", "系统设计"],
    },

    # ── Specialized engineering ──────────────────────────────────────────
    "game-developer": {
        "role_family": "software_development",
        "salary_p50": 25000, "replacement_pressure": 45, "human_ai_leverage": 58, "career_level": 3,
        "core_tasks": ["游戏逻辑开发", "引擎开发", "渲染优化", "物理模拟", "网络同步"],
        "display_skills": ["C++", "Unity", "Unreal", "OpenGL", "Python", "Lua"],
    },
    "qa": {
        "role_family": "quality_assurance",
        "salary_p50": 18000, "replacement_pressure": 62, "human_ai_leverage": 55, "career_level": 2,
        "core_tasks": ["测试用例设计", "自动化测试", "性能测试", "质量保障", "缺陷管理"],
        "display_skills": ["Selenium", "Python", "JMeter", "Postman", "SQL", "Git"],
    },
    "cyber-security": {
        "role_family": "devops_infra",
        "salary_p50": 28000, "replacement_pressure": 18, "human_ai_leverage": 75, "career_level": 3,
        "core_tasks": ["渗透测试", "安全评估", "漏洞修复", "安全架构", "应急响应"],
        "display_skills": ["Python", "Linux", "Wireshark", "Burp Suite", "Nmap", "OWASP"],
    },
    "devsecops": {
        "role_family": "devops_infra",
        "salary_p50": 28000, "replacement_pressure": 22, "human_ai_leverage": 72, "career_level": 3,
        "core_tasks": ["安全流水线", "合规审计", "容器安全", "密钥管理", "威胁建模"],
        "display_skills": ["Docker", "Kubernetes", "Terraform", "Vault", "SAST/DAST", "Python"],
    },

    # ── Language-specific ───────────────────────────────────────────────
    "cpp": {
        "role_family": "software_development",
        "salary_p50": 26000, "replacement_pressure": 22, "human_ai_leverage": 62, "career_level": 3,
        "core_tasks": ["系统编程", "性能优化", "底层开发", "引擎开发", "嵌入式开发"],
        "display_skills": ["C++", "STL", "CMake", "GDB", "多线程", "Linux"],
    },
    "rust": {
        "role_family": "software_development",
        "salary_p50": 30000, "replacement_pressure": 18, "human_ai_leverage": 65, "career_level": 3,
        "core_tasks": ["系统编程", "安全编程", "WebAssembly", "基础设施", "并发开发"],
        "display_skills": ["Rust", "Cargo", "Tokio", "WebAssembly", "Linux", "Docker"],
    },
    "python": {
        "role_family": "software_development",
        "salary_p50": 24000, "replacement_pressure": 40, "human_ai_leverage": 70, "career_level": 2,
        "core_tasks": ["后端开发", "数据处理", "自动化脚本", "AI应用", "Web开发"],
        "display_skills": ["Python", "Django", "FastAPI", "Pandas", "Docker", "PostgreSQL"],
    },
    "java": {
        "role_family": "software_development",
        "salary_p50": 25000, "replacement_pressure": 38, "human_ai_leverage": 62, "career_level": 3,
        "core_tasks": ["企业应用开发", "微服务", "中间件", "分布式系统", "性能调优"],
        "display_skills": ["Java", "Spring Boot", "MySQL", "Redis", "Kafka", "Docker"],
    },
    "golang": {
        "role_family": "software_development",
        "salary_p50": 28000, "replacement_pressure": 28, "human_ai_leverage": 68, "career_level": 3,
        "core_tasks": ["微服务开发", "云原生应用", "中间件", "高并发系统", "基础设施"],
        "display_skills": ["Go", "gRPC", "Docker", "Kubernetes", "MySQL", "Redis"],
    },
    "kotlin": {
        "role_family": "software_development",
        "salary_p50": 24000, "replacement_pressure": 38, "human_ai_leverage": 60, "career_level": 2,
        "core_tasks": ["Android开发", "Kotlin后端", "跨平台开发", "协程编程", "SDK开发"],
        "display_skills": ["Kotlin", "Android SDK", "Jetpack", "Coroutines", "Gradle", "Room"],
    },
    "php": {
        "role_family": "software_development",
        "salary_p50": 18000, "replacement_pressure": 58, "human_ai_leverage": 52, "career_level": 2,
        "core_tasks": ["Web开发", "CMS开发", "API开发", "Laravel应用", "电商系统"],
        "display_skills": ["PHP", "Laravel", "MySQL", "Redis", "Nginx", "Composer"],
    },

    # ── Framework-specific ──────────────────────────────────────────────
    "react": {
        "role_family": "software_development",
        "salary_p50": 24000, "replacement_pressure": 45, "human_ai_leverage": 65, "career_level": 2,
        "core_tasks": ["React应用开发", "状态管理", "组件库开发", "SSR/SSG", "性能优化"],
        "display_skills": ["React", "TypeScript", "Redux", "Next.js", "Webpack", "Jest"],
    },
    "vue": {
        "role_family": "software_development",
        "salary_p50": 22000, "replacement_pressure": 45, "human_ai_leverage": 62, "career_level": 2,
        "core_tasks": ["Vue应用开发", "组件开发", "状态管理", "工程化", "性能优化"],
        "display_skills": ["Vue.js", "TypeScript", "Pinia", "Vite", "Element Plus", "Nuxt"],
    },
    "angular": {
        "role_family": "software_development",
        "salary_p50": 23000, "replacement_pressure": 42, "human_ai_leverage": 58, "career_level": 2,
        "core_tasks": ["Angular应用开发", "企业级前端", "RxJS", "模块化架构", "性能优化"],
        "display_skills": ["Angular", "TypeScript", "RxJS", "NgRx", "Jasmine", "Webpack"],
    },
    "nodejs": {
        "role_family": "software_development",
        "salary_p50": 24000, "replacement_pressure": 42, "human_ai_leverage": 66, "career_level": 2,
        "core_tasks": ["Node.js后端", "BFF层开发", "实时应用", "工具链开发", "SSR"],
        "display_skills": ["Node.js", "Express", "TypeScript", "MongoDB", "Redis", "GraphQL"],
    },

    # ── Infrastructure ──────────────────────────────────────────────────
    "kubernetes": {
        "role_family": "devops_infra",
        "salary_p50": 28000, "replacement_pressure": 25, "human_ai_leverage": 68, "career_level": 3,
        "core_tasks": ["集群管理", "容器编排", "服务治理", "自动扩缩容", "CICD集成"],
        "display_skills": ["Kubernetes", "Docker", "Helm", "Prometheus", "Istio", "Linux"],
    },
    "linux": {
        "role_family": "devops_infra",
        "salary_p50": 22000, "replacement_pressure": 30, "human_ai_leverage": 62, "career_level": 2,
        "core_tasks": ["系统管理", "Shell脚本", "网络配置", "故障排查", "性能优化"],
        "display_skills": ["Linux", "Bash", "Nginx", "iptables", "systemd", "Docker"],
    },
    "docker": {
        "role_family": "devops_infra",
        "salary_p50": 24000, "replacement_pressure": 32, "human_ai_leverage": 66, "career_level": 2,
        "core_tasks": ["容器化部署", "镜像管理", "Docker Compose", "CI集成", "安全加固"],
        "display_skills": ["Docker", "Docker Compose", "Linux", "Nginx", "CI/CD", "Git"],
    },
    "postgresql-dba": {
        "role_family": "data_engineering",
        "salary_p50": 25000, "replacement_pressure": 42, "human_ai_leverage": 58, "career_level": 3,
        "core_tasks": ["数据库管理", "性能调优", "备份恢复", "高可用方案", "SQL优化"],
        "display_skills": ["PostgreSQL", "SQL", "Linux", "Python", "Redis", "监控"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# Supplementary edges — natural career transitions missing from frontmatter
# ═══════════════════════════════════════════════════════════════════════════
# Format: (source, target, difficulty, reason)
# difficulty: 低=same domain, 中=adjacent, 高=cross-domain

SUPPLEMENTARY_EDGES: list[tuple[str, str, str, str]] = [
    # AI/Data cluster connectivity
    ("ai-engineer", "mlops", "低", "AI工程→模型运维，技能高度重叠"),
    ("ai-engineer", "data-engineer", "中", "AI需要数据管线能力"),
    ("ai-engineer", "machine-learning", "低", "AI工程 vs ML工程，核心共通"),
    ("machine-learning", "data-engineer", "中", "特征工程与数据管线重叠"),
    ("machine-learning", "data-analyst", "低", "都需数据分析+统计能力"),
    ("mlops", "devops", "低", "MLOps是DevOps在ML领域的延伸"),
    ("data-analyst", "data-engineer", "中", "分析→工程，SQL/Python共通"),
    ("data-analyst", "python", "低", "Python是数据分析核心语言"),

    # Mobile cluster
    ("android", "ios", "中", "移动双平台，架构思维相通"),
    ("android", "flutter", "低", "Android→Flutter跨平台"),
    ("android", "kotlin", "低", "Kotlin是Android主力语言"),
    ("ios", "flutter", "低", "iOS→Flutter跨平台"),
    ("ios", "react-native", "中", "RN也能做iOS"),
    ("flutter", "react-native", "低", "都是跨平台移动框架"),
    ("android", "frontend", "中", "都涉及UI/交互开发"),
    ("ios", "frontend", "中", "都涉及UI/交互开发"),

    # Frontend framework cluster
    ("vue", "react", "低", "前端框架互转成本低"),
    ("vue", "angular", "低", "前端框架互转"),
    ("react", "angular", "中", "React→Angular需适应强约定"),
    ("vue", "frontend", "低", "Vue是前端核心框架"),
    ("angular", "frontend", "低", "Angular是前端核心框架"),
    ("react", "frontend", "低", "React是前端核心框架"),

    # Backend language cluster
    ("golang", "backend", "低", "Go是主流后端语言"),
    ("golang", "devops", "低", "Go在云原生基础设施广泛使用"),
    ("golang", "kubernetes", "低", "K8s/Docker用Go写的"),
    ("php", "backend", "低", "PHP是传统Web后端"),
    ("php", "nodejs", "中", "都做Web后端"),

    # Infrastructure cluster
    ("docker", "kubernetes", "低", "容器→编排，自然升级路径"),
    ("docker", "devops", "低", "Docker是DevOps核心工具"),
    ("docker", "linux", "低", "容器跑在Linux上"),
    ("kubernetes", "linux", "低", "K8s依赖Linux知识"),
    ("devsecops", "devops", "低", "DevSecOps = DevOps + 安全"),
    ("devsecops", "cyber-security", "低", "安全方向的DevOps实践"),
    ("devsecops", "docker", "中", "容器安全是DevSecOps重点"),

    # Cross-domain career progressions
    ("game-developer", "cpp", "低", "C++是游戏主力语言"),
    ("game-developer", "frontend", "中", "游戏前端/Web游戏方向"),
    ("software-architect", "full-stack", "低", "架构需全栈视野"),
    ("software-architect", "engineering-manager", "低", "技术专家→管理双通道"),
    ("engineering-manager", "backend", "中", "多数工程经理出身后端"),
    ("qa", "software-architect", "高", "测试→架构，需大量补充"),
    ("qa", "devsecops", "中", "测试→安全测试方向"),
    ("postgresql-dba", "backend", "中", "DBA→后端，数据库能力复用"),
    ("postgresql-dba", "data-engineer", "低", "DBA→数据工程，存储能力复用"),

    # Language → framework natural links
    ("kotlin", "android", "低", "Kotlin是Android主力语言"),
    ("kotlin", "java", "低", "Kotlin/Java互操作"),
    ("java", "software-architect", "中", "Java生态丰富，架构师路径"),

    # Fix low-degree nodes
    ("kotlin", "backend", "中", "Kotlin Server-Side/Spring方向"),
    ("kotlin", "flutter", "中", "移动开发集群互转"),
    ("engineering-manager", "devops", "中", "DevOps/SRE管理方向"),
    ("engineering-manager", "full-stack", "中", "全栈技术管理"),
    ("engineering-manager", "frontend", "中", "前端团队管理"),
    ("engineering-manager", "golang", "中", "Go团队技术管理方向"),

    # Machine learning needs more connections
    ("machine-learning", "mlops", "低", "训练→部署闭环"),
    ("machine-learning", "backend", "中", "ML模型服务化"),

    # Chinese market common stacks
    ("vue", "full-stack", "中", "Vue全栈方向"),
    ("angular", "full-stack", "中", "Angular企业全栈"),
    ("golang", "rust", "中", "系统编程语言互转"),
    ("php", "vue", "中", "PHP+Vue经典全栈搭配"),
    ("php", "frontend", "中", "PHP全栈→前端"),
    ("postgresql-dba", "devops", "中", "DBA运维交叉"),
]


# ── Known tech terms for display skill filtering ───────────────────────
# Skills containing these tokens are good display candidates.
_TECH_TOKENS = {
    # Languages
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
    "kotlin", "swift", "php", "ruby", "sql", "dart", "scala", "lua",
    # Frameworks / Libraries
    "react", "vue", "angular", "next.js", "nuxt", "svelte", "django", "flask",
    "spring", "express", "fastapi", "laravel", "rails",
    "pytorch", "tensorflow", "scikit", "pandas", "numpy",
    "flutter", "jetpack", "swiftui",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "sqlite", "cassandra",
    "elasticsearch", "neo4j",
    # Tools / Platforms
    "docker", "kubernetes", "git", "github", "gitlab", "jenkins", "terraform",
    "ansible", "nginx", "apache", "kafka", "rabbitmq", "graphql", "grpc",
    "webpack", "vite", "babel",
    # Concepts (short, recognizable)
    "rest", "api", "ci/cd", "microservices", "serverless", "oauth", "jwt",
    "websocket", "ssr", "pwa", "orm", "tdd", "devops",
    # AI/ML
    "llm", "rag", "embeddings", "transformers", "hugging face", "openai",
    "vector database", "fine-tuning", "prompt engineering",
    # Cloud
    "aws", "gcp", "azure",
}


def _pick_display_skills(skills: list[str], max_count: int = 6) -> list[str]:
    """Pick recognizable tech keywords from a skill list for map display.

    Prefers: known framework/language/tool names over generic descriptions.
    Falls back to shortest non-question skills if no tech terms found.
    """
    picked: list[str] = []
    seen_lower: set[str] = set()

    # Pass 1: exact tech term matches
    for s in skills:
        if len(picked) >= max_count:
            break
        sl = s.lower().strip()
        if sl in seen_lower:
            continue
        # Check if any known tech token appears in the skill name
        for tok in _TECH_TOKENS:
            if tok in sl:
                picked.append(s)
                seen_lower.add(sl)
                break

    # Pass 2: short, non-question skills (likely tool/concept names)
    if len(picked) < max_count:
        for s in skills:
            if len(picked) >= max_count:
                break
            sl = s.lower().strip()
            if sl in seen_lower:
                continue
            # Skip questions, long descriptions, too-generic items
            if "?" in s or len(s) > 30 or s.startswith(("Learn ", "What ", "How ", "Why ")):
                continue
            # Prefer short names (likely proper nouns)
            if len(s) <= 20:
                picked.append(s)
                seen_lower.add(sl)

    return picked[:max_count]


def _derive_zone(rp: float, hal: float) -> str:
    """Derive zone from replacement_pressure and human_ai_leverage."""
    if hal >= 65 and rp < 40:
        return "leverage"
    if hal - rp > 25:
        return "safe"
    if rp >= 58:
        return "danger"
    return "transition"


def build_graph() -> dict:
    """Build graph.json from roadmap_skills.json + curated metadata."""
    with open(_INPUT, "r", encoding="utf-8") as f:
        roles = json.load(f)

    nodes = []
    edges = []
    edge_set: set[tuple[str, str]] = set()

    # ── Build nodes ────────────────────────────────────────────────────
    for role_id, role_data in roles.items():
        meta = ROLE_META.get(role_id)
        if not meta:
            print(f"  WARN: no metadata for {role_id}, skipping")
            continue

        rp = meta["replacement_pressure"]
        hal = meta["human_ai_leverage"]
        zone = _derive_zone(rp, hal)

        # Top skills for map display — use curated display_skills if available,
        # otherwise pick recognizable tech keywords from the roadmap
        all_skills = role_data.get("skills", [])
        must_skills = meta.get("display_skills") or _pick_display_skills(all_skills, max_count=6)

        node = {
            "node_id": role_id,
            "label": role_data.get("label", role_id),
            "role_family": meta["role_family"],
            "zone": zone,
            "replacement_pressure": rp,
            "human_ai_leverage": hal,
            "salary_p50": meta["salary_p50"],
            "career_level": meta["career_level"],
            "must_skills": must_skills,
            "core_tasks": meta.get("core_tasks", []),
            "topics": role_data.get("topics", []),
            "skill_count": role_data.get("skill_count", len(all_skills)),
        }
        nodes.append(node)

    node_ids = {n["node_id"] for n in nodes}

    # ── Build edges from related_roles (bidirectional) ─────────────────
    for role_id, role_data in roles.items():
        if role_id not in node_ids:
            continue
        for related in role_data.get("related_roles", []):
            if related not in node_ids:
                continue
            edge_key = tuple(sorted([role_id, related]))
            if edge_key not in edge_set:
                edge_set.add(edge_key)
                edges.append({
                    "source": role_id,
                    "target": related,
                    "edge_type": "related",
                    "difficulty": "中",
                })

    # ── Add supplementary edges ────────────────────────────────────────
    supp_added = 0
    for src, tgt, diff, reason in SUPPLEMENTARY_EDGES:
        if src not in node_ids or tgt not in node_ids:
            continue
        edge_key = tuple(sorted([src, tgt]))
        if edge_key not in edge_set:
            edge_set.add(edge_key)
            edges.append({
                "source": src,
                "target": tgt,
                "edge_type": "supplementary",
                "difficulty": diff,
            })
            supp_added += 1

    graph = {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "version": "2.0-roadmap",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "source": "developer-roadmap + curated metadata",
        },
    }

    print(f"\nGraph built:")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Edges: {len(edges)} (related: {len(edges) - supp_added}, supplementary: {supp_added})")

    return graph


def validate_graph(graph: dict) -> bool:
    """Run quality checks on the generated graph."""
    nodes = graph["nodes"]
    edges = graph["edges"]
    node_ids = {n["node_id"] for n in nodes}

    ok = True

    # 1. Connectivity check (bidirectional BFS)
    adj: dict[str, set[str]] = {nid: set() for nid in node_ids}
    for e in edges:
        s, t = e["source"], e["target"]
        if s in adj and t in adj:
            adj[s].add(t)
            adj[t].add(s)

    visited: set[str] = set()
    queue = [next(iter(node_ids))]
    visited.add(queue[0])
    while queue:
        n = queue.pop(0)
        for nb in adj[n]:
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)

    if visited != node_ids:
        print(f"  FAIL: disconnected nodes: {node_ids - visited}")
        ok = False
    else:
        print(f"  OK: fully connected")

    # 2. Degree distribution
    degrees = {nid: len(nb) for nid, nb in adj.items()}
    min_deg = min(degrees.values())
    max_deg = max(degrees.values())
    avg_deg = sum(degrees.values()) / len(degrees)
    fragile = [nid for nid, d in degrees.items() if d <= 1]
    print(f"  Degrees: min={min_deg}, max={max_deg}, avg={avg_deg:.1f}")
    if fragile:
        print(f"  WARN: fragile nodes (degree<=1): {fragile}")
    else:
        print(f"  OK: no fragile nodes")

    # 3. Zone distribution
    zones: dict[str, int] = {}
    for n in nodes:
        z = n["zone"]
        zones[z] = zones.get(z, 0) + 1
    print(f"  Zones: {dict(sorted(zones.items()))}")

    # 4. Role family distribution
    families: dict[str, int] = {}
    for n in nodes:
        f = n["role_family"]
        families[f] = families.get(f, 0) + 1
    print(f"  Families: {dict(sorted(families.items()))}")

    # 5. Salary range
    salaries = [n["salary_p50"] for n in nodes]
    print(f"  Salary range: {min(salaries)}-{max(salaries)} RMB/month")

    # 6. Dangling edge references
    for e in edges:
        if e["source"] not in node_ids:
            print(f"  FAIL: dangling edge source: {e['source']}")
            ok = False
        if e["target"] not in node_ids:
            print(f"  FAIL: dangling edge target: {e['target']}")
            ok = False

    return ok


def main():
    print("Building career graph from roadmap data...\n")

    graph = build_graph()

    print("\nValidation:")
    valid = validate_graph(graph)

    if not valid:
        print("\nGraph has issues — NOT saving.")
        return

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to {_OUTPUT}")


if __name__ == "__main__":
    main()
