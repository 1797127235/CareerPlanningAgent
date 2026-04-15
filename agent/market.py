"""市场信号查询 — 单一数据源。

对外四个入口：
  - resolve_direction(query) 把任意输入（中文方向名/node_id/别名/子串）解析到规范 role_family
  - get_signal(query)        返回富化后的信号（带 top_industries 和解析后的规范名）
  - get_signal_for_node(id)  向后兼容：按 node_id 查
  - all_signals()            整张表（给 global summary 用）
  - available_directions()   可查询的方向列表（用于 tool miss 时提示 LLM）

数据来自 data/ 下三个 JSON 文件，懒加载 + 进程级缓存。
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
}


def _load_once() -> None:
    global _market_signals, _industry_signals, _graph_family_map
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
    except Exception as e:
        logger.warning("graph.json load failed: %s", e)
        _graph_family_map = {}


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


def resolve_direction(query: str) -> Optional[str]:
    """把用户/LLM 输入解析到规范 role_family。

    顺序：
      1. 精确匹配（包含 proxy，外部调用者可能需要 proxy 家族如"架构"）
      2. 忽略大小写精确匹配
      3. 别名表
      4. node_id → role_family（via graph.json）
      5. 唯一子串匹配（仅非 proxy 家族，避免歧义）

    任何一步无法唯一确定都返回 None — 绝不猜测。
    """
    if not query:
        return None
    _load_once()
    assert _market_signals is not None and _graph_family_map is not None

    q = query.strip()
    if not q:
        return None

    if q in _market_signals:
        return q

    q_lower = q.lower()
    for key in _market_signals:
        if key.lower() == q_lower:
            return key

    alias = _ALIASES.get(q_lower)
    if alias and alias in _market_signals:
        return alias

    if q in _graph_family_map:
        fam = _graph_family_map[q]
        if fam in _market_signals:
            return fam

    matches = [
        k for k in _market_signals
        if not _market_signals[k].get("is_proxy") and (q in k or k in q)
    ]
    if len(matches) == 1:
        return matches[0]

    return None


def get_signal(query: str) -> Optional[dict]:
    """返回规范家族的富化信号（含 top_industries 和 _resolved_family）。

    Resolver miss 时返回 None — 调用方负责展示"无数据"和可用方向。
    """
    family = resolve_direction(query)
    if not family:
        return None
    _load_once()
    sig = (_market_signals or {}).get(family)
    if not sig:
        return None
    sig = dict(sig)
    sig["_resolved_family"] = family
    sig["top_industries"] = (_industry_signals or {}).get(family, [])[:3]
    return sig


def get_signal_for_node(node_id: str) -> Optional[dict]:
    """向后兼容：supervisor 的 context builder 传的是 node_id。"""
    return get_signal(node_id)
