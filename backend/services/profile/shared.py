# -*- coding: utf-8 -*-
"""Shared constants and utilities for profile service sub-modules."""
from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

FAMILY_KEYWORDS: dict[str, list[str]] = {
    "quality_assurance": [
        "测试", "QA", "质量保证", "用例", "缺陷", "Bug", "自动化测试",
        "软件测试", "测试工程", "Selenium", "Pytest", "JMeter", "LoadRunner",
        "测试用例", "冒烟测试", "回归测试", "接口测试", "性能测试", "安全测试",
        "白盒", "黑盒", "ISTQB",
    ],
    "software_development": [
        "开发", "编程", "前端", "后端", "全栈", "程序员", "React", "Vue",
        "Angular", "Node.js", "Spring", "Django", "Flask", "Rails",
        "API开发", "组件开发", "页面开发", "APP开发", "游戏开发",
    ],
    "后端开发": [
        "后端", "服务端", "Server", "后台", "API", "微服务", "高并发",
        "分布式", "RPC", "消息队列", "缓存", "网关", "负载均衡",
    ],
    "系统开发": [
        "系统开发", "系统编程", "底层", "内核", "操作系统", "文件系统",
        "内存管理", "存储引擎", "数据库内核", "性能优化", "性能调优",
        "网络编程", "Linux编程", "系统架构", "基础架构", "Infrastructure",
    ],
    "algorithm_ai": [
        "算法", "机器学习", "深度学习", "NLP", "CV", "人工智能", "大模型",
        "LLM", "推荐系统", "神经网络", "模型训练", "PyTorch", "TensorFlow",
        "强化学习", "自然语言处理", "图像识别", "目标检测", "自动驾驶",
    ],
    "data_engineering": [
        "数据工程", "ETL", "数据仓库", "大数据", "数据平台", "Spark", "Flink",
        "Hadoop", "Hive", "Kafka", "数据治理", "数据中台", "实时计算",
    ],
    "data_analysis": [
        "数据分析", "BI", "商业分析", "数据可视化", "Tableau", "Power BI",
        "数据挖掘", "运营分析",
    ],
    "devops_infra": [
        "运维", "DevOps", "SRE", "云原生", "容器", "Kubernetes", "Docker",
        "CI/CD", "网络工程", "系统管理", "DBA", "监控", "K8s",
    ],
    "embedded_hardware": [
        "嵌入式", "单片机", "FPGA", "硬件", "芯片", "固件", "PCB", "MCU",
        "ARM", "Verilog", "IoT", "物联网", "电路",
    ],
    "product_design": [
        "UI设计", "UX", "交互设计", "视觉设计", "用户研究", "Figma", "Sketch",
        "产品设计", "设计师",
    ],
    "product_management": [
        "产品经理", "产品运营", "需求管理", "产品规划", "用户增长", "竞品分析",
        "PRD",
    ],
    "delivery_and_support": [
        "实施工程", "技术支持", "售前", "售后", "客户成功", "IT支持", "系统管理",
    ],
}

_SOFT_DIM_ZH = {
    "communication": "沟通能力",
    "learning": "学习能力",
    "resilience": "抗压能力",
    "innovation": "创新能力",
    "collaboration": "协作能力",
}


def _soft_skills_as_list(raw) -> list[str]:
    """Normalize soft_skills to a list of Chinese label strings.

    Handles both legacy list-of-str and new dict-of-scores formats.
    """
    if isinstance(raw, dict):
        return [_SOFT_DIM_ZH.get(k, k) for k, v in raw.items() if isinstance(v, (int, float)) and v >= 3]
    if isinstance(raw, list):
        return [s.strip() for s in raw if isinstance(s, str) and s.strip()]
    return []
