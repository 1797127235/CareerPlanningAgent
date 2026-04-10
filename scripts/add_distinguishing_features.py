"""
Add distinguishing_features + not_this_role_if to all graph nodes.
Solves the root problem of similar-skill roles being indistinguishable.
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# node_id -> (distinguishing_features, not_this_role_if)
FEATURES: dict[str, tuple[list[str], list[str]]] = {
    "algorithm-engineer": (
        ["有顶会/CCF论文经历", "深耕垂类算法（推荐/风控/异常检测）", "数学竞赛/建模获奖", "算法创新与理论推导"],
        ["主要做模型部署和MLOps", "无算法创新经历，偏调包调参", "以工程交付为主"],
    ),
    "machine-learning": (
        ["大规模模型训练与部署", "推荐/广告/搜索系统工程经验", "MLOps与模型上线意识", "以工程交付和A/B测试为主"],
        ["偏纯理论研究、无工程落地经验", "主要写学术论文而非上线系统"],
    ),
    "ai-engineer": (
        ["LLM应用开发（RAG/Agent/Prompt）", "LangChain/LangGraph/MCP等AI框架", "多模型编排与集成", "AI产品工程化落地"],
        ["传统ML算法研究", "无LLM/Agent开发经验"],
    ),
    "ai-data-scientist": (
        ["统计建模与假设检验", "A/B实验设计与业务洞察", "数据可视化与分析报告", "Jupyter/R/业务指标建模"],
        ["主要做算法工程/模型部署", "无业务数据分析经验"],
    ),
    "ml-architect": (
        ["ML系统整体架构设计", "带领算法团队或管理技术方向", "跨团队技术决策经验", "5年以上ML工程经验"],
        ["刚入门ML、缺乏系统设计经验", "个人贡献者阶段"],
    ),
    "ai-ml-architect": (
        ["AI/ML系统架构师级别设计能力", "分布式训练/推理优化", "云平台ML服务设计", "技术领导力"],
        ["初中级工程师阶段", "只做模型训练而非系统架构"],
    ),
    "frontend": (
        ["React/Vue/Next.js项目主导", "UI/UX实现与前端工程化", "以浏览器端交互开发为主"],
        ["后端API开发者偶尔写前端", "全栈但偏后端"],
    ),
    "full-stack": (
        ["前后端都能独立交付", "独立开发完整产品", "Node.js/TypeScript+后端框架"],
        ["专精某一端（纯前端或纯后端）", "无前端工程化经验"],
    ),
    "devops": (
        ["CI/CD流水线主导设计", "Kubernetes集群运维与管理", "基础设施即代码（Terraform/Ansible）", "SRE或运维岗经验"],
        ["只是在开发项目中用过Docker/Linux", "以业务代码开发为主"],
    ),
    "devsecops": (
        ["安全左移/SAST/DAST集成到CI/CD", "合规审计与漏洞扫描", "DevOps+安全职责双重覆盖"],
        ["纯DevOps无安全背景", "传统安全工程师无DevOps经验"],
    ),
    "java-engineer": (
        ["Spring Boot/Spring Cloud微服务", "高并发/分布式Java系统", "MySQL/Redis/Kafka后端栈"],
        ["Python/Go开发者", "前端或数据方向"],
    ),
    "python-engineer": (
        ["Python Web开发（Django/FastAPI）", "Python自动化脚本与工具链", "以Python作为主开发语言交付业务系统"],
        ["Python只是辅助工具（如ML研究用Python）", "数据分析为主"],
    ),
    "go-engineer": (
        ["Go语言微服务/高并发系统", "云原生Go后端开发", "gRPC/服务治理经验"],
        ["主要用Java/Python开发", "无Go项目经验"],
    ),
    "cpp-engineer": (
        ["C++高性能系统/底层开发", "内存管理/多线程C++项目", "游戏引擎/嵌入式/音视频等C++方向"],
        ["主要用高级语言开发业务逻辑", "C++只是大学课程"],
    ),
    "rust-engineer": (
        ["Rust系统编程/安全并发", "Rust WebAssembly或底层库开发"],
        ["Rust只是学过但无项目经验", "主要使用其他语言"],
    ),
    "android-engineer": (
        ["Android原生应用开发（Kotlin/Java）", "Jetpack组件/Android SDK经验", "以移动端为主要交付形态"],
        ["只做Web前端", "跨平台框架为主（Flutter/RN）"],
    ),
    "ios-engineer": (
        ["Swift/SwiftUI原生iOS开发", "iOS SDK/Xcode项目经验"],
        ["Android或跨平台为主", "只做Web前端"],
    ),
    "flutter-engineer": (
        ["Flutter跨平台开发（Dart）", "同时发布iOS和Android应用", "Flutter为主要技术栈"],
        ["原生iOS/Android开发者", "Web前端"],
    ),
    "react-native-engineer": (
        ["React Native移动开发", "JS/TS跨平台移动应用"],
        ["原生移动开发者", "纯Web前端"],
    ),
    "game-client-engineer": (
        ["Unity/Unreal游戏客户端开发", "游戏引擎C++/C#实战经验", "图形学/渲染/Shader开发"],
        ["普通Web或后端开发者", "只用UE5做AI Avatar等非游戏项目"],
    ),
    "game-server-engineer": (
        ["游戏服务器/战斗逻辑C++/Go", "KCP/UDP游戏网络协议", "高并发游戏场景后端"],
        ["普通业务后端", "无游戏服务器特有经验"],
    ),
    "data-engineer": (
        ["数据管道/ETL/Flink/Spark开发", "数据仓库建设", "以数据流/存储系统开发为主"],
        ["数据分析/报表为主", "ML算法工程师"],
    ),
    "data-analyst": (
        ["业务数据分析/SQL报表/Dashboard", "用数据回答业务问题", "Excel/Tableau/Power BI等分析工具"],
        ["数据工程/管道开发", "ML算法开发"],
    ),
    "bi-analyst": (
        ["BI工具（Power BI/Tableau）开发报表", "数据仓库建模/指标体系设计", "为业务方提供数据洞察"],
        ["ML算法工程师", "数据管道开发"],
    ),
    "data-architect": (
        ["数据架构师/数据治理", "数仓整体架构设计（ODS/DWD/DWS/ADS）", "数据标准与质量体系"],
        ["业务数据分析师", "ML工程师"],
    ),
    "database-engineer": (
        ["PostgreSQL/MySQL深度优化", "数据库内核/存储引擎", "DBA或数据库专项工程师"],
        ["普通后端用SQL", "数据分析师"],
    ),
    "network-security-engineer": (
        ["渗透测试/漏洞挖掘/安全审计", "Wireshark/Burp Suite/Nmap等安全工具实战", "CVE分析/CTF竞赛经历"],
        ["普通后端开发者做了安全模块", "无攻防实战经验"],
    ),
    "ai-security-engineer": (
        ["LLM安全（越狱/对抗攻击/Prompt Injection）", "AI系统Red Teaming", "模型安全评估与防御"],
        ["传统网络安全工程师无LLM经验", "普通AI工程师"],
    ),
    "blockchain-engineer": (
        ["Solidity智能合约开发", "EVM/Web3.js/DeFi协议实战", "区块链底层原理理解"],
        ["Web后端开发者", "无区块链实战经验"],
    ),
    "test-engineer": (
        ["自动化测试框架开发（Selenium/Pytest/JMeter）", "测试用例设计与质量体系建设", "以测试为主要职责"],
        ["开发工程师偶尔写单元测试", "无系统化测试经验"],
    ),
    "test-architect": (
        ["测试架构/自动化测试平台设计", "测试策略与质量体系架构师级别"],
        ["初级测试工程师", "开发工程师"],
    ),
    "software-architect": (
        ["系统架构设计/技术选型决策", "DDD/微服务架构实践", "带领团队的架构师经验"],
        ["个人贡献者阶段", "初中级工程师"],
    ),
    "cloud-architect": (
        ["AWS/阿里云云架构设计", "多云/混合云架构方案", "Kubernetes集群与云原生架构"],
        ["只是日常使用云服务", "无云架构设计经验"],
    ),
    "engineering-manager": (
        ["管理3人以上工程团队", "OKR制定与团队规划", "以人员管理为主要职责"],
        ["纯技术个人贡献者", "无管理经验"],
    ),
    "cto": (
        ["CTO/VPE级别技术战略", "公司级技术方向制定", "10人以上技术团队管理"],
        ["初中级工程师", "无管理经验"],
    ),
    "product-manager": (
        ["产品需求分析/用户研究", "PRD撰写与产品迭代规划", "以产品视角而非技术视角主导工作"],
        ["纯技术开发者", "无产品规划经验"],
    ),
    "ux-designer": (
        ["Figma/Sketch交互设计", "用户研究与可用性测试", "以设计输出为主要职责"],
        ["前端开发者偶尔做UI", "无设计专业训练"],
    ),
    "tech-writer": (
        ["API文档/技术写作为主职", "Docs-as-Code流程", "为开发者受众撰写技术内容"],
        ["开发者偶尔写README", "无专业技术写作经验"],
    ),
    "developer-relations": (
        ["Developer Advocacy/技术布道", "开发者社区运营", "以外部开发者影响力为主要工作"],
        ["纯内部开发工程师", "无社区运营经验"],
    ),
    "mlops-engineer": (
        ["MLOps平台/模型训练流水线", "模型版本管理与线上服务化", "Airflow/Kubeflow/MLflow实战"],
        ["只做模型算法研究", "普通DevOps无ML背景"],
    ),
}


def run():
    path = DATA / "graph.json"
    with open(path, encoding="utf-8") as f:
        graph = json.load(f)

    updated = 0
    skipped = []
    for node in graph["nodes"]:
        nid = node["node_id"]
        if nid in FEATURES:
            df, ntrf = FEATURES[nid]
            node["distinguishing_features"] = df
            node["not_this_role_if"] = ntrf
            updated += 1
        else:
            skipped.append(nid)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"Updated {updated} nodes with distinguishing_features")
    if skipped:
        print(f"Skipped (no features defined): {skipped}")


if __name__ == "__main__":
    run()
