"""Market signal card extraction for coach responses."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy-loaded caches
_market_signals_for_cards: dict | None = None
_graph_family_map_for_cards: dict | None = None

# Node ID → short readable label for card preview
_NODE_LABELS: dict[str, str] = {
    "java": "Java", "python": "Python", "golang": "Go", "cpp": "C++", "rust": "Rust",
    "frontend": "前端", "full-stack": "全栈", "android": "Android", "ios": "iOS",
    "flutter": "Flutter", "react-native": "RN", "ai-engineer": "AI工程师",
    "machine-learning": "ML", "ai-data-scientist": "AI数据", "ai-agents": "AI Agent",
    "mlops": "MLOps", "ml-architect": "ML架构", "algorithm-engineer": "算法",
    "data-analyst": "数据分析", "data-engineer": "数据工程", "bi-analyst": "BI",
    "postgresql-dba": "DBA", "data-architect": "数据架构",
    "devops": "DevOps", "devsecops": "DevSecOps", "cloud-architect": "云架构",
    "game-developer": "游戏开发", "server-side-game-developer": "游戏服务端",
    "cyber-security": "网络安全", "ai-red-teaming": "AI红队", "security-architect": "安全架构",
    "qa": "测试", "qa-lead": "测试负责人",
    "product-manager": "产品经理", "engineering-manager": "技术管理", "cto": "CTO",
    "search-engine-engineer": "搜索引擎", "storage-database-kernel": "存储内核",
    "infrastructure-engineer": "基础设施", "software-architect": "软件架构",
}

_ALIASES: dict[str, list[str]] = {
    "AI/ML":       ["AI/ML", "AI方向", "AI 方向", "人工智能", "机器学习", "深度学习", "大模型", "LLM", "AIGC"],
    "后端开发":    ["后端开发", "后端方向", "服务端开发", "后台开发", "Java", "Python", "Golang", "Go语言", "SpringBoot"],
    "系统开发":    ["系统开发", "系统软件", "底层开发", "内核开发", "基础架构", "中间件", "C++", "Rust"],
    "前端开发":    ["前端开发", "前端方向", "前端工程", "Vue.js", "React.js", "Next.js", "Angular", "TypeScript"],
    "数据":        ["数据方向", "数据分析", "数据工程", "大数据", "数仓", "数据仓库", "数据科学", "BI"],
    "移动开发":    ["移动开发", "移动端", "App开发", "Android", "iOS", "Flutter"],
    "游戏开发":    ["游戏开发", "游戏客户端", "游戏引擎", "Unity", "UE4", "UE5"],
    "运维/DevOps": ["运维开发", "运维方向", "DevOps", "云原生", "Kubernetes", "k8s", "SRE"],
    "安全":        ["安全方向", "网络安全", "信息安全", "渗透测试", "红蓝对抗"],
    "质量保障":    ["质量保障", "测试开发", "自动化测试"],
    "产品":        ["产品方向", "产品经理", "产品设计"],
    "管理":        ["技术管理", "工程管理", "CTO"],
}

_ASCII_ONLY = re.compile(r"^[A-Za-z0-9+#.\-/ ]+$")


def _load_market_signals() -> dict:
    global _market_signals_for_cards
    if _market_signals_for_cards is None:
        try:
            data = Path(__file__).resolve().parent.parent.parent.parent / "data" / "market_signals.json"
            _market_signals_for_cards = json.loads(data.read_text(encoding="utf-8"))
        except Exception:
            _market_signals_for_cards = {}
    return _market_signals_for_cards or {}


def _kw_hit(kw: str, body: str) -> bool:
    if _ASCII_ONLY.match(kw):
        pat = rf"(?<![A-Za-z0-9]){re.escape(kw.strip())}(?![A-Za-z0-9])"
        return bool(re.search(pat, body))
    return kw in body


def extract_market_cards(text: str) -> list[dict]:
    """Detect market direction mentions in coach response, return signal cards for frontend.

    Emitted as market_cards SSE event so frontend can render inline data cards.
    Only fires for coach_agent responses that reference market directions.
    """
    signals = _load_market_signals()
    if not signals:
        return []

    cards = []
    seen: set[str] = set()

    for family, aliases in _ALIASES.items():
        if family in seen or family not in signals:
            continue
        sig = signals[family]
        if sig.get("is_proxy"):
            continue
        matched = any(_kw_hit(kw, text) for kw in aliases)
        if not matched:
            continue

        node_ids = sig.get("node_ids", [])
        role_examples = [_NODE_LABELS.get(n, n) for n in node_ids[:3]]
        cards.append({
            "family": family,
            "timing": sig.get("timing"),
            "timing_label": sig.get("timing_label", ""),
            "demand_change_pct": sig.get("demand_change_pct", 0),
            "salary_cagr": sig.get("salary_cagr", 0),
            "node_id": node_ids[0] if node_ids else None,
            "role_examples": role_examples,
        })
        seen.add(family)

    return cards[:4]  # Cap at 4 to avoid UI clutter


def get_card_for_node(node_id: str) -> dict | None:
    """Get a market signal card for a specific graph node_id."""
    global _graph_family_map_for_cards
    signals = _load_market_signals()

    if _graph_family_map_for_cards is None:
        try:
            gdata = Path(__file__).resolve().parent.parent.parent.parent / "data" / "graph.json"
            nodes = json.loads(gdata.read_text(encoding="utf-8")).get("nodes", [])
            _graph_family_map_for_cards = {n["node_id"]: n.get("role_family", "") for n in nodes}
        except Exception:
            _graph_family_map_for_cards = {}

    role_family = (_graph_family_map_for_cards or {}).get(node_id, "")
    if not role_family or role_family not in signals:
        return None

    sig = signals[role_family]
    if sig.get("is_proxy"):
        proxy_family = sig.get("proxy_family", "")
        if proxy_family and proxy_family in signals:
            sig = signals[proxy_family]
            role_family = proxy_family

    node_ids = sig.get("node_ids", [])
    role_examples = [_NODE_LABELS.get(n, n) for n in node_ids[:3]]

    return {
        "family": role_family,
        "timing": sig.get("timing"),
        "timing_label": sig.get("timing_label", ""),
        "demand_change_pct": sig.get("demand_change_pct", 0),
        "salary_cagr": sig.get("salary_cagr", 0),
        "node_id": node_id,
        "role_examples": role_examples,
    }
