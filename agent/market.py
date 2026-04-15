"""市场信号查询 — 单一数据源。

对外入口：
  - resolve_direction(query) 把任意非空输入映射到某个 market family（6 层兜底，永不返回 None）
  - get_signal(query)        返回富化后的信号（带 top_industries 和解析后的规范名 + 置信度）
  - get_signal_for_node(id)  向后兼容：按 node_id 查
  - all_signals()            整张表（给 global summary 用）
  - available_directions()   有数据的方向列表

设计决定：对 coach 场景，resolver **不会 miss**。
任何非空 query 都会被映射到 12 个 family 里的一个（关键词分类 + 终极 fallback 到 AI/ML）。
调用方不再需要处理"无数据"路径——这个路径会让 coach 说"系统里没有 X 方向的数据"，产品上不接受。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_market_signals: Optional[dict[str, dict]] = None
_industry_signals: Optional[dict[str, list]] = None
_graph_family_map: Optional[dict[str, str]] = None  # node_id → role_family
_graph_label_map: Optional[dict[str, str]] = None   # label_cn / label(lower) → role_family


# 常见别名 / 口语化说法 → 规范 role_family。
# 只收录无歧义映射；有歧义的（如 "系统" 同时对应 "系统开发" 和 "系统软件"）留给 resolver 子串匹配走兜底。
# key 一律小写，resolver 会对查询做 lower() 后匹配。
_ALIASES: dict[str, str] = {
    # 后端
    "后端": "后端开发",
    "后台": "后端开发",
    "服务端": "后端开发",
    "backend": "后端开发",
    # 前端
    "前端": "前端开发",
    "frontend": "前端开发",
    # AI / 算法
    "ai": "AI/ML",
    "ml": "AI/ML",
    "ai/ml": "AI/ML",
    "机器学习": "AI/ML",
    "深度学习": "AI/ML",
    "算法": "AI/ML",
    "大模型": "AI/ML",
    "llm": "AI/ML",
    # 运维
    "devops": "运维/DevOps",
    "运维": "运维/DevOps",
    "sre": "运维/DevOps",
    # 数据
    "data": "数据",
    "大数据": "数据",
    "数据开发": "数据",
    "数据工程": "数据",
    "数据分析": "数据",
    # QA
    "qa": "质量保障",
    "测试": "质量保障",
    "测试开发": "质量保障",
    # 移动
    "移动": "移动开发",
    "android": "移动开发",
    "安卓": "移动开发",
    "ios": "移动开发",
    # 全栈
    "全栈": "全栈开发",
    "fullstack": "全栈开发",
    # 架构
    "架构师": "架构",
    # 产品
    "产品经理": "产品",
    "pm": "产品",
    # 安全
    "security": "安全",
    "信息安全": "安全",
    "网络安全": "安全",
    # 游戏
    "游戏": "游戏开发",
    "gamedev": "游戏开发",
    # 管理 — 工程经理 / 技术总监 / tech lead 等带人岗
    "工程经理": "管理",
    "技术经理": "管理",
    "技术主管": "管理",
    "技术总监": "管理",
    "cto": "管理",
    "engineering manager": "管理",
    "em": "管理",
    "tech lead": "管理",
    "leader": "管理",
    # Graph 里有 family 但 market_signals 没有，映射到最接近的 market family
    "区块链": "后端开发",
    "web3": "后端开发",
    "嵌入式": "系统开发",
    "硬件": "系统开发",
    "嵌入式开发": "系统开发",
}


# 关键词 → family 分类器。用于 graph 标签 / 别名 / 子串都匹配不到时的兜底。
# 顺序有意义：更具体 / 更强信号的类别放前面。
_KEYWORD_BUCKETS: list[tuple[tuple[str, ...], str]] = [
    # 管理类（"经理/主管/总监/leader" 是强信号，放最前避免被"算法工程师的经理"之类误分到 AI）
    (("经理", "主管", "总监", "leader", "lead", "manager", "director", "head of", "带团队", "带人"), "管理"),
    # AI / 算法
    (("算法", "机器学习", "深度学习", "神经网络", "模型训练", "推理", "ai", "ml", "llm", "大模型",
      "transformer", "nlp", "cv", "计算机视觉", "强化学习", "agi", "aigc", "炼丹"), "AI/ML"),
    # 前端
    (("前端", "frontend", "react", "vue", "angular", "css", "javascript", "typescript", "h5", "web ui",
      "小程序", "浏览器"), "前端开发"),
    # 数据
    (("数据", "etl", "数仓", "bi", "数据分析", "数据工程", "数据库", "大数据", "spark", "flink",
      "hadoop", "sql", "数仓", "analytics"), "数据"),
    # 运维 / DevOps / 云
    (("运维", "devops", "sre", "kubernetes", "k8s", "ci/cd", "platform", "云计算", "cloud",
      "infra", "基础设施"), "运维/DevOps"),
    # 安全
    (("安全", "security", "渗透", "红队", "蓝队", "攻防", "防御", "cyber", "漏洞", "逆向"), "安全"),
    # 游戏
    (("游戏", "gamedev", "unity", "unreal", "虚幻", "客户端游戏", "服务端游戏"), "游戏开发"),
    # 移动
    (("移动", "mobile", "ios", "android", "安卓", "app开发", "flutter", "react native", "跨平台"), "移动开发"),
    # 产品
    (("产品", "pm", "product"), "产品"),
    # 系统 / 底层 / 嵌入式
    (("系统", "底层", "内核", "驱动", "嵌入式", "硬件", "cpp", "c++", "固件", "操作系统",
      "存储", "数据库内核", "编译器", "虚拟机", "搜索引擎"), "系统开发"),
    # 测试
    (("测试", "qa", "quality", "自动化测试"), "质量保障"),
    # 后端（通用兜底，放较后——很多前后端通用词都会先被前面分走）
    (("后端", "后台", "服务端", "backend", "server", "api", "rpc", "分布式", "中间件",
      "高并发", "微服务", "java", "golang", "go 语言", "python 后端", "node.js",
      "区块链", "blockchain", "web3", "defi", "智能合约", "solidity"), "后端开发"),
]


def _heuristic_family(q_lower: str) -> str:
    """关键词分类器。任何输入都会命中一条—最后还有 AI/ML 兜底。"""
    for keywords, family in _KEYWORD_BUCKETS:
        if any(kw in q_lower for kw in keywords):
            return family
    # 终极兜底：对无关键词命中的查询，默认 AI/ML（CS 场景最常问、最活跃）
    return "AI/ML"


# Graph 里有但 market_signals 里没有的 family → 最接近的 market family。
# 用于 graph_label 匹配返回非 market family 时的二次兜底。
_NON_MARKET_FAMILY_FALLBACK: dict[str, str] = {
    "区块链": "后端开发",
    "嵌入式/硬件": "系统开发",
    "社区": "产品",
    "文档": "产品",
    "设计": "产品",
}


def _load_once() -> None:
    global _market_signals, _industry_signals, _graph_family_map, _graph_label_map
    if _market_signals is not None:
        return
    try:
        _market_signals = json.loads((_DATA_DIR / "market_signals.json").read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("market_signals.json load failed: %s", e)
        _market_signals = {}
    try:
        _industry_signals = json.loads((_DATA_DIR / "industry_signals.json").read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("industry_signals.json load failed: %s", e)
        _industry_signals = {}
    try:
        nodes = json.loads((_DATA_DIR / "graph.json").read_text(encoding="utf-8")).get("nodes", [])
        _graph_family_map = {n["node_id"]: n.get("role_family", "") for n in nodes if n.get("node_id")}
        # 构建 label → family 查找表（label_cn + label 英文 lowercased 都收录）
        label_map: dict[str, str] = {}
        for n in nodes:
            fam = n.get("role_family", "")
            if not fam:
                continue
            if (lc := n.get("label_cn")):
                label_map[lc] = fam
                label_map[lc.lower()] = fam
            if (le := n.get("label")):
                label_map[le] = fam
                label_map[le.lower()] = fam
        _graph_label_map = label_map
    except Exception as e:
        logger.warning("graph.json load failed: %s", e)
        _graph_family_map = {}
        _graph_label_map = {}


def all_signals() -> dict[str, dict]:
    _load_once()
    return _market_signals or {}


def available_directions(include_proxy: bool = False) -> list[str]:
    """有真实数据的方向列表。默认剔除 is_proxy（代理数据，不展示给用户）。"""
    _load_once()
    return [
        k for k, v in (_market_signals or {}).items()
        if include_proxy or not v.get("is_proxy")
    ]


def resolve_direction_ranked(query: str) -> tuple[Optional[str], str]:
    """把 query 解析到 market family + 置信度标签。

    置信度：
      exact       用户直接说了某 family 名
      alias       别名表直中
      node_id     node_id 匹配（e.g. supervisor context 传的）
      graph_label node 的 label_cn/label 匹配（e.g. "工程经理"→engineering-manager→管理）
      substring   家族名子串唯一命中
      heuristic   关键词兜底（有方向但不在已知数据的映射）
      fallback    完全无关键词，兜底到 AI/ML

    空输入返回 (None, "empty")。非空输入**永不返回 None 的 family**。
    """
    if not query:
        return None, "empty"
    _load_once()
    assert _market_signals is not None and _graph_family_map is not None and _graph_label_map is not None

    q = query.strip()
    if not q:
        return None, "empty"

    if q in _market_signals:
        return q, "exact"

    q_lower = q.lower()
    for key in _market_signals:
        if key.lower() == q_lower:
            return key, "exact"

    alias = _ALIASES.get(q_lower)
    if alias and alias in _market_signals:
        return alias, "alias"

    if q in _graph_family_map:
        fam = _graph_family_map[q]
        if fam in _market_signals:
            return fam, "node_id"

    label_fam = _graph_label_map.get(q) or _graph_label_map.get(q_lower)
    if label_fam:
        if label_fam in _market_signals:
            return label_fam, "graph_label"
        fallback_fam = _NON_MARKET_FAMILY_FALLBACK.get(label_fam)
        if fallback_fam and fallback_fam in _market_signals:
            return fallback_fam, "graph_label"

    matches = [
        k for k in _market_signals
        if not _market_signals[k].get("is_proxy") and (q in k or k in q)
    ]
    if len(matches) == 1:
        return matches[0], "substring"

    fam = _heuristic_family(q_lower)
    # _heuristic_family 返回的家族保证存在（都是 market_signals 已知的 12 个真实 family 之一）
    # 如果终极兜底（"AI/ML"）被触发，用 "fallback" 标签；有关键词命中用 "heuristic"
    conf = "fallback" if not any(
        any(kw in q_lower for kw in keywords) for keywords, _ in _KEYWORD_BUCKETS
    ) else "heuristic"
    return fam, conf


def resolve_direction(query: str) -> Optional[str]:
    """resolve_direction_ranked 的薄包装（保留向后兼容）。"""
    fam, _ = resolve_direction_ranked(query)
    return fam


def get_signal(query: str) -> Optional[dict]:
    """返回 family 的富化信号（含 top_industries / _resolved_family / _confidence）。

    空 query 返回 None；任何非空 query 都会返回某个 family 的 signal（resolver 不 miss）。
    """
    family, confidence = resolve_direction_ranked(query)
    if not family:
        return None
    _load_once()
    sig = (_market_signals or {}).get(family)
    if not sig:
        return None
    sig = dict(sig)
    sig["_resolved_family"] = family
    sig["_confidence"] = confidence
    sig["top_industries"] = (_industry_signals or {}).get(family, [])[:3]
    return sig


def get_signal_for_node(node_id: str) -> Optional[dict]:
    """严格按 node_id 查，miss 返回 None。

    和 get_signal 不同，这里 miss 不走 heuristic/fallback——因为 node_id 是内部 ID，
    不是用户输入，garbage 进来时不该伪造数据污染 supervisor 上下文。
    """
    if not node_id:
        return None
    _load_once()
    assert _graph_family_map is not None and _market_signals is not None
    fam = _graph_family_map.get(node_id, "")
    if not fam:
        return None
    if fam not in _market_signals:
        fam = _NON_MARKET_FAMILY_FALLBACK.get(fam, "")
        if not fam or fam not in _market_signals:
            return None
    sig = dict(_market_signals[fam])
    sig["_resolved_family"] = fam
    sig["_confidence"] = "node_id"
    sig["top_industries"] = (_industry_signals or {}).get(fam, [])[:3]
    return sig
