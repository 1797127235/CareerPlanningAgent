"""
Local translation of roadmap skills — no API calls.
Uses a comprehensive EN→ZH dictionary for CS/tech terms.

Usage: python -m backend.scripts.translate_roadmap_local
"""

import json
from pathlib import Path

SKILLS_PATH = Path("data/roadmap_skills.json")

# Comprehensive EN→ZH dictionary for developer skills
EN_ZH = {
    # Programming concepts
    "Diamond Inheritance": "菱形继承",
    "Forward Declaration": "前向声明",
    "Code Editors / IDEs": "代码编辑器 / IDE",
    "Running your First Program": "运行第一个程序",
    "Arithmetic Operators": "算术运算符",
    "Logical Operators": "逻辑运算符",
    "Bitwise Operators": "位运算符",
    "for / while / do while loops": "循环语句",
    "if else / switch / goto": "条件语句",
    "Static Polymorphism": "静态多态",
    "Function Overloading": "函数重载",
    "Operator Overloading": "运算符重载",
    "Lambdas": "Lambda 表达式",
    "Static Typing": "静态类型",
    "Dynamic Typing": "动态类型",
    "RTTI": "运行时类型识别",
    "References": "引用",
    "Memory Model": "内存模型",
    "Lifetime of Objects": "对象生命周期",
    "Smart Pointers": "智能指针",
    "weak_ptr": "weak_ptr",
    "shared_ptr": "shared_ptr",
    "unique_ptr": "unique_ptr",
    "Raw Pointers": "裸指针",
    "Pointers and References": "指针与引用",
    "Data Types": "数据类型",
    "Functions": "函数",
    "Control Flow & Statements": "控制流",
    "Basic Operations": "基本操作",
    "Exception Handling": "异常处理",
    "Language Concepts": "语言概念",
    "Standard Library + STL": "标准库 + STL",
    "Templates": "模板",
    "Idioms": "惯用法",
    "Standards": "语言标准",
    "Debuggers": "调试器",
    "Compilers": "编译器",
    "Build Systems": "构建系统",
    "Package Managers": "包管理器",
    "Working with Libraries": "使用库",
    "Structuring Codebase": "代码组织",
    "Structures and Classes": "结构体与类",
    "Introduction to Language": "语言入门",
    "Setting up your Environment": "环境搭建",
    "Basic Syntax": "基础语法",
    "Conditionals": "条件语句",
    "Type Casting": "类型转换",
    "Arrays": "数组",
    "Strings": "字符串",
    "Variables": "变量",
    "Data Structures": "数据结构",
    "Algorithms": "算法",
    "Recursion": "递归",
    "Sorting Algorithms": "排序算法",
    "Search Algorithms": "搜索算法",
    "Dynamic Programming": "动态规划",
    "Graph Theory": "图论",
    "Tree": "树",
    "Binary Tree": "二叉树",
    "Hash Table": "哈希表",
    "Linked List": "链表",
    "Stack": "栈",
    "Queue": "队列",
    "Heap": "堆",
    "Concurrency": "并发",
    "Multithreading": "多线程",
    "Thread Pool": "线程池",
    "Mutex": "互斥锁",
    "Async": "异步编程",
    "Coroutines": "协程",
    "Closures": "闭包",
    "Iterators": "迭代器",
    "Generics": "泛型",
    "Interfaces": "接口",
    "Abstract Classes": "抽象类",
    "Inheritance": "继承",
    "Polymorphism": "多态",
    "Encapsulation": "封装",
    "Design Patterns": "设计模式",
    "OOP": "面向对象编程",
    "Functional Programming": "函数式编程",
    "Error Handling": "错误处理",
    "Regular Expressions": "正则表达式",
    "Serialization": "序列化",
    "Dependency Injection": "依赖注入",
    # Architecture
    "Levels of Architecture": "架构层级",
    "Application Architecture": "应用架构",
    "Solution Architecture": "解决方案架构",
    "Enterprise Architecture": "企业架构",
    "System Design": "系统设计",
    "Microservices": "微服务",
    "Monolithic": "单体架构",
    "Serverless": "无服务器",
    "Event Driven": "事件驱动",
    "CQRS": "命令查询分离",
    "Domain Driven Design": "领域驱动设计",
    "Design Patterns": "设计模式",
    "Architectural Patterns": "架构模式",
    "Design and Development Principles": "设计与开发原则",
    "Building For Scale": "构建可扩展系统",
    "Scaling Databases": "数据库扩展",
    # Web / Backend
    "Internet": "互联网基础",
    "Search Engines": "搜索引擎",
    "Learn about APIs": "API 基础",
    "REST": "REST API",
    "GraphQL": "GraphQL",
    "gRPC": "gRPC",
    "WebSockets": "WebSocket",
    "Authentication": "认证",
    "Authorization": "授权",
    "OAuth": "OAuth",
    "JWT": "JWT",
    "Cookie Based Auth": "Cookie 认证",
    "Basic Authentication": "基础认证",
    "Web Security": "Web 安全",
    "CORS": "跨域资源共享",
    "CSP": "内容安全策略",
    "HTTPS": "HTTPS",
    "SSL / TLS": "SSL / TLS",
    "Caching": "缓存",
    "CDN": "CDN",
    "Message Brokers": "消息队列",
    "Real-Time Data": "实时数据",
    "Testing": "测试",
    "Unit Testing": "单元测试",
    "Integration Testing": "集成测试",
    "CI / CD": "CI / CD",
    "Containerization vs Virtualization": "容器化与虚拟化",
    "Version Control Systems": "版本控制",
    "Repo Hosting Services": "代码托管服务",
    "Web Servers": "Web 服务器",
    "Relational Databases": "关系型数据库",
    "NoSQL Databases": "NoSQL 数据库",
    "More about Databases": "数据库进阶",
    "Pick a Language": "选择编程语言",
    "Learn a Programming Language": "学习编程语言",
    # Databases
    "PostgreSQL": "PostgreSQL",
    "MySQL": "MySQL",
    "MongoDB": "MongoDB",
    "Redis": "Redis",
    "Elasticsearch": "Elasticsearch",
    "Cassandra": "Cassandra",
    "ACID": "ACID 特性",
    "CAP Theorem": "CAP 定理",
    "Transactions": "事务",
    "Indexes": "索引",
    "Normalization": "范式化",
    "N+1 Problem": "N+1 查询问题",
    # DevOps / Infra
    "Docker": "Docker",
    "Kubernetes": "Kubernetes",
    "Terraform": "Terraform",
    "Ansible": "Ansible",
    "Linux": "Linux",
    "Nginx": "Nginx",
    "Apache": "Apache",
    "Load Balancing": "负载均衡",
    "Reverse Proxy": "反向代理",
    "Monitoring": "监控",
    "Logging": "日志",
    "Cloud Computing": "云计算",
    "Containerization": "容器化",
    "Infrastructure as Code": "基础设施即代码",
    "Service Mesh": "服务网格",
    "Networking": "网络",
    # Frontend
    "HTML": "HTML",
    "CSS": "CSS",
    "JavaScript": "JavaScript",
    "TypeScript": "TypeScript",
    "Responsive Design": "响应式设计",
    "State Management": "状态管理",
    "Component Architecture": "组件架构",
    "Build Tools": "构建工具",
    "Performance Optimization": "性能优化",
    "Accessibility": "无障碍",
    "SEO": "搜索引擎优化",
    "Browser DevTools": "浏览器开发工具",
    # Mobile
    "Kotlin": "Kotlin",
    "Java": "Java",
    "Swift Basics": "Swift 基础",
    "Objective-C": "Objective-C",
    "Objective-C Basics": "Objective-C 基础",
    "Benefits over Objective-C": "Swift 相比 OC 的优势",
    "Development IDE": "开发 IDE",
    # Data / AI
    "Machine Learning": "机器学习",
    "Deep Learning": "深度学习",
    "NLP": "自然语言处理",
    "Data Analysis": "数据分析",
    "Data Visualization": "数据可视化",
    "Data Pipeline": "数据管道",
    "Feature Engineering": "特征工程",
    "Model Training": "模型训练",
    "Python": "Python",
    "Go": "Go",
    "Rust": "Rust",
    "Bash": "Bash",
    "Git": "Git",
    "GitHub": "GitHub",
    "npm": "npm",
    # Security
    "OWASP": "OWASP",
    "Cryptography": "密码学",
    "Penetration Testing": "渗透测试",
    "Network Security": "网络安全",
    # Catch-all patterns
    "Installing": "安装",
    "Overview": "概述",
    "Introduction": "介绍",
    "Fundamentals": "基础",
    "Best Practices": "最佳实践",
    "Advanced": "进阶",
}


def _translate(skill: str) -> str:
    """Translate a skill name, trying exact match first, then partial."""
    # Exact match
    if skill in EN_ZH:
        return EN_ZH[skill]

    # Case-insensitive exact
    lower = skill.lower()
    for en, zh in EN_ZH.items():
        if en.lower() == lower:
            return zh

    # Already Chinese or a proper noun (keep as-is)
    if any("\u4e00" <= c <= "\u9fff" for c in skill):
        return skill

    # Partial pattern matching for common prefixes/suffixes
    for pattern, replacement in EN_ZH.items():
        if len(pattern) >= 4 and pattern.lower() in lower:
            return skill  # keep original if it's a compound (e.g., "Rust REPL")

    return skill  # no translation found, keep English


def main():
    with open(SKILLS_PATH, "r", encoding="utf-8") as f:
        roles = json.load(f)

    translated = 0
    kept = 0

    for role_id, role_data in roles.items():
        skills_en = role_data.get("skills", [])
        skills_zh = []
        for s in skills_en:
            zh = _translate(s)
            skills_zh.append(zh)
            if zh != s:
                translated += 1
            else:
                kept += 1
        role_data["skills_zh"] = skills_zh

    with open(SKILLS_PATH, "w", encoding="utf-8") as f:
        json.dump(roles, f, ensure_ascii=False, indent=2)

    print(f"Done: {translated} translated, {kept} kept as-is")
    print(f"Translation rate: {translated / (translated + kept) * 100:.1f}%")

    # Show sample
    cpp = roles.get("cpp", {})
    print("\nC++ sample:")
    for en, zh in zip(cpp.get("skills", [])[:10], cpp.get("skills_zh", [])[:10]):
        flag = "  " if en == zh else "→ "
        print(f"  {flag}{en:35s}  {zh}")


if __name__ == "__main__":
    main()
