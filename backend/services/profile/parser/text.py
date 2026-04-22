"""Text-based extraction helpers (skills, certificates, truncation)."""
from __future__ import annotations

import json
import logging
import re

from backend.services.profile.parser.normalize import _normalize_skill_name

logger = logging.getLogger(__name__)

# ── Skill extraction from project descriptions (fallback when LLM misses tech skills) ──

# Keywords that indicate a technology/skill mentioned in project descriptions.
# These supplement the LLM-extracted skills when the model misses tech terms.
_PROJECT_TECH_KEYWORDS: dict[str, str] = {
    # Languages
    "python": "Python", "c++": "C++", "cpp": "C++", "java": "Java",
    "javascript": "JavaScript", "typescript": "TypeScript", "go": "Go",
    "rust": "Rust", "c#": "C#", "csharp": "C#", "php": "PHP", "ruby": "Ruby",
    "swift": "Swift", "kotlin": "Kotlin", "dart": "Dart", "r语言": "R",
    "matlab": "MATLAB", "scala": "Scala", "shell": "Shell", "bash": "Bash",
    "sql": "SQL", "html": "HTML", "css": "CSS",
    # Deep Learning / ML Frameworks
    "pytorch": "PyTorch", "tensorflow": "TensorFlow", "keras": "Keras",
    "paddle": "PaddlePaddle", "mindspore": "MindSpore", "jax": "JAX",
    "huggingface": "Hugging Face", "transformers": "Hugging Face",
    "onnx": "ONNX", "tensorrt": "TensorRT", "openvino": "OpenVINO",
    "scikit-learn": "Scikit-learn", "sklearn": "Scikit-learn",
    "xgboost": "XGBoost", "lightgbm": "LightGBM", "catboost": "CatBoost",
    # CV / Imaging
    "opencv": "OpenCV", "pillow": "Pillow", "opencv-python": "OpenCV",
    "图像分割": "图像分割", "语义分割": "语义分割", "实例分割": "实例分割",
    "目标检测": "目标检测", "图像分类": "图像分类",
    "三维重建": "三维重建", "nerf": "NeRF", "3d reconstruction": "三维重建",
    "计算机视觉": "计算机视觉", "cv": "计算机视觉",
    "医学图像": "医学图像处理", "医学图像处理": "医学图像处理",
    "medical image": "医学图像处理",
    "mamba": "Mamba", "state space model": "Mamba", "state space": "Mamba",
    "cnn": "CNN", "卷积神经网络": "CNN",
    "transformer": "Transformer", "transformers": "Transformer",
    "unet": "U-Net", "u-net": "U-Net", "u net": "U-Net",
    "medsam": "MedSAM", "sam": "SAM",
    "gan": "GAN", "生成对抗网络": "GAN",
    "diffusion": "Diffusion", "扩散模型": "Diffusion",
    "resnet": "ResNet", "residual network": "ResNet",
    "vit": "ViT", "vision transformer": "ViT",
    "yolo": "YOLO", "yolov": "YOLO",
    "mobilenet": "MobileNet", "efficientnet": "EfficientNet",
    "densenet": "DenseNet", "inception": "Inception",
    "注意力机制": "注意力机制", "attention": "注意力机制",
    "数据增强": "数据增强", "augmentation": "数据增强",
    "迁移学习": "迁移学习", "transfer learning": "迁移学习",
    "领域自适应": "领域自适应", "domain adaptation": "领域自适应",
    "domain generalization": "域泛化", "域泛化": "域泛化",
    "半监督学习": "半监督学习", "semi-supervised learning": "半监督学习",
    "自监督学习": "自监督学习", "self-supervised learning": "自监督学习",
    "对比学习": "对比学习", "contrastive learning": "对比学习",
    "多模态": "多模态", "multimodal": "多模态",
    "少样本学习": "少样本学习", "few-shot learning": "少样本学习",
    "增量学习": "增量学习", "continual learning": "增量学习",
    "联邦学习": "联邦学习", "federated learning": "联邦学习",
    # DL / ML Concepts
    "深度学习": "深度学习", "deep learning": "深度学习",
    "机器学习": "机器学习", "machine learning": "机器学习",
    "神经网络": "神经网络", "neural network": "神经网络",
    "强化学习": "强化学习", "reinforcement learning": "强化学习",
    "自然语言处理": "自然语言处理", "nlp": "自然语言处理",
    "大语言模型": "大语言模型", "llm": "大语言模型", "large language model": "大语言模型",
    "rag": "RAG", "retrieval augmented generation": "RAG",
    "特征工程": "特征工程", "feature engineering": "特征工程",
    "模型微调": "模型微调", "fine-tuning": "模型微调", "finetune": "模型微调",
    "模型蒸馏": "模型蒸馏", "knowledge distillation": "模型蒸馏",
    "量化": "量化部署", "quantization": "量化部署",
    "模型部署": "模型部署", "model deployment": "模型部署",
    "模型压缩": "模型压缩", "model compression": "模型压缩",
    "超参数调优": "超参数调优", "hyperparameter tuning": "超参数调优",
    "交叉验证": "交叉验证", "cross validation": "交叉验证",
    # Data / Analytics
    "numpy": "NumPy", "pandas": "Pandas", "matplotlib": "Matplotlib",
    "seaborn": "Seaborn", "plotly": "Plotly",
    "scipy": "SciPy", "statsmodels": "Statsmodels",
    "spark": "Spark", "flink": "Flink", "hadoop": "Hadoop",
    "kafka": "Kafka", "rabbitmq": "RabbitMQ", "rocketmq": "RocketMQ",
    "airflow": "Airflow", "dolphinscheduler": "DolphinScheduler",
    "dbt": "dbt",
    "数据仓库": "数据仓库", "data warehouse": "数据仓库",
    "etl": "ETL", "数据 pipeline": "ETL",
    "数据挖掘": "数据挖掘", "data mining": "数据挖掘",
    "数据分析": "数据分析", "data analysis": "数据分析",
    "数据可视化": "数据可视化", "data visualization": "数据可视化",
    "数据清洗": "数据清洗", "data cleaning": "数据清洗",
    "ab test": "A/B测试", "ab测试": "A/B测试", "a/b test": "A/B测试",
    "tableau": "Tableau", "powerbi": "Power BI", "finebi": "FineBI",
    # DB
    "mysql": "MySQL", "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "mongodb": "MongoDB", "redis": "Redis", "elasticsearch": "Elasticsearch",
    "sqlite": "SQLite", "oracle": "Oracle",
    "clickhouse": "ClickHouse", "doris": "Doris",
    "neo4j": "Neo4j",
    # Backend / Web
    "django": "Django", "flask": "Flask", "fastapi": "FastAPI", "tornado": "Tornado",
    "spring": "Spring", "springboot": "Spring Boot", "spring cloud": "Spring Cloud",
    "express": "Express", "koa": "Koa", "egg": "Egg.js",
    "gin": "Gin", "echo": "Echo",
    "grpc": "gRPC", "protobuf": "Protocol Buffers",
    "restful": "RESTful API", "rest api": "RESTful API", "graphql": "GraphQL",
    "websocket": "WebSocket",
    "nginx": "Nginx", "apache": "Apache",
    "celery": "Celery", "rabbit mq": "RabbitMQ",
    # Frontend
    "react": "React", "vue": "Vue.js", "angular": "Angular",
    "next.js": "Next.js", "nuxt": "Nuxt.js",
    "webpack": "Webpack", "vite": "Vite", "rollup": "Rollup", "parcel": "Parcel",
    "babel": "Babel", "eslint": "ESLint", "prettier": "Prettier",
    "sass": "Sass", "less": "Less", "postcss": "PostCSS",
    "tailwind": "Tailwind CSS", "bootstrap": "Bootstrap", "antd": "Ant Design",
    "jquery": "jQuery", "d3": "D3.js", "echarts": "ECharts",
    "three.js": "Three.js", "webgl": "WebGL",
    "electron": "Electron", "tauri": "Tauri",
    "pwa": "PWA", "service worker": "PWA",
    "ssr": "SSR", "csr": "CSR", "服务端渲染": "SSR",
    # Mobile
    "android": "Android", "ios": "iOS",
    "flutter": "Flutter", "react native": "React Native",
    "uniapp": "uni-app", "小程序": "微信小程序", "微信小程序": "微信小程序",
    # Cloud / DevOps / Infra
    "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "jenkins": "Jenkins", "gitlab ci": "GitLab CI", "github actions": "GitHub Actions",
    "ansible": "Ansible", "terraform": "Terraform", "pulumi": "Pulumi",
    "prometheus": "Prometheus", "grafana": "Grafana",
    "istio": "Istio", "envoy": "Envoy",
    "aws": "AWS", "阿里云": "阿里云", "腾讯云": "腾讯云", "华为云": "华为云",
    "azure": "Azure", "gcp": "GCP",
    "serverless": "Serverless", "faas": "Serverless",
    "ci/cd": "CI/CD", "cicd": "CI/CD",
    "微服务": "微服务", "microservices": "微服务",
    "服务网格": "服务网格", "service mesh": "服务网格",
    "负载均衡": "负载均衡", "load balancing": "负载均衡",
    # Security
    "渗透测试": "渗透测试", "网络安全": "网络安全",
    "密码学": "密码学", "cryptography": "密码学",
    "区块链": "区块链", "blockchain": "区块链",
    "solidity": "Solidity", "web3": "Web3", "ethereum": "Ethereum",
    # Other tools
    "git": "Git", "github": "GitHub", "gitlab": "GitLab", "gitee": "Gitee",
    "linux": "Linux", "ubuntu": "Linux", "centos": "Linux",
    "vim": "Vim", "vscode": "VS Code",
    "jupyter": "Jupyter", "notebook": "Jupyter",
    "anaconda": "Anaconda", "conda": "Conda", "pip": "pip",
    "cmake": "CMake", "makefile": "Makefile", "ninja": "Ninja",
    "latex": "LaTeX", "overleaf": "LaTeX",
    "markdown": "Markdown", "md": "Markdown",
    "cuda": "CUDA", "cudnn": "cuDNN",
    "mpi": "MPI", "openmp": "OpenMP",
    "spark": "Spark", "hadoop": "Hadoop", "hive": "Hive",
    "ftp": "FTP", "sftp": "SFTP",
    # Project / Collaboration
    "敏捷开发": "Agile", "scrum": "Scrum", "kanban": "Kanban",
    "jira": "Jira", "confluence": "Confluence", "notion": "Notion",
    "figma": "Figma", "sketch": "Sketch", "axure": "Axure",
    "postman": "Postman", "swagger": "Swagger", "apidoc": "API文档",
    "sonarqube": "SonarQube", "codecov": "Code Coverage",
    "单元测试": "单元测试", "集成测试": "集成测试", "自动化测试": "自动化测试",
    "selenium": "Selenium", "playwright": "Playwright", "cypress": "Cypress",
    "pytest": "Pytest", "unittest": "unittest", "jest": "Jest",
    "持续集成": "CI/CD", "持续部署": "CI/CD",
}


def _extract_skills_from_text(text: str) -> list[dict]:
    """Extract skills from free-text by keyword matching against _PROJECT_TECH_KEYWORDS.

    Returns list of {name, level} dicts with level='familiar'.
    Avoids duplicates (case-insensitive).
    Uses word-boundary matching for short ASCII keywords to reduce false positives.
    """
    if not text:
        return []
    text_lower = text.lower()
    found: set[str] = set()
    result: list[dict] = []
    for keyword, canonical in _PROJECT_TECH_KEYWORDS.items():
        kw_lower = keyword.lower()
        # Word-boundary matching for ASCII keywords (avoids "java" matching "javascript")
        matched = False
        if kw_lower.isascii():
            import re
            pattern = r'(?<![a-z0-9])' + re.escape(kw_lower) + r'(?![a-z0-9])'
            if re.search(pattern, text_lower):
                matched = True
        else:
            if kw_lower in text_lower:
                matched = True

        if matched and canonical.lower() not in found:
            found.add(canonical.lower())
            result.append({"name": canonical, "level": "familiar"})
    return result


def _supplement_skills_from_projects(parsed: dict) -> dict:
    """When LLM/VLM extracts too few skills, supplement from project descriptions.

    Scans projects, internship tech_stack/highlights, and raw_text for
    technology keywords and adds them as familiar-level skills.
    """
    existing_names = {s.get("name", "").lower() for s in parsed.get("skills", []) if isinstance(s, dict)}
    if len(existing_names) >= 5:
        # Already enough skills, skip supplement
        return parsed

    sources: list[str] = []

    # 1. Project descriptions
    for proj in parsed.get("projects", []):
        if isinstance(proj, str):
            sources.append(proj)
        elif isinstance(proj, dict):
            sources.append(proj.get("name", ""))
            sources.append(proj.get("description", ""))
            sources.append(proj.get("highlights", ""))
            tech = proj.get("tech_stack") or proj.get("technologies") or []
            if isinstance(tech, list):
                sources.append(", ".join(str(t) for t in tech))
            elif isinstance(tech, str):
                sources.append(tech)

    # 2. Internship tech_stack and highlights
    for intern in parsed.get("internships", []):
        if isinstance(intern, dict):
            sources.append(intern.get("highlights", ""))
            tech = intern.get("tech_stack") or []
            if isinstance(tech, list):
                sources.append(", ".join(str(t) for t in tech))
            elif isinstance(tech, str):
                sources.append(tech)

    # 3. Raw text (last resort)
    raw = parsed.get("raw_text", "")
    if raw and not raw.startswith("[multimodal_extracted]"):
        sources.append(raw)

    combined = " ".join(str(s) for s in sources if s)
    supplemental = _extract_skills_from_text(combined)

    added = 0
    for skill in supplemental:
        name = skill["name"]
        if name.lower() not in existing_names:
            parsed.setdefault("skills", []).append(skill)
            existing_names.add(name.lower())
            added += 1

    if added:
        logger.info("Supplemented %d skills from project descriptions", added)
    return parsed


# ── Certificate regex fallback ───────────────────────────────────────────────

_CERTIFICATE_PATTERNS: list[tuple[str, str]] = [
    # English / Language
    (r"CET[-\s]?4", "英语（CET-4）"),
    (r"CET[-\s]?6", "英语（CET-6）"),
    (r"BEC\s*(高级|中级|初级|Higher|Vantage|Preliminary)?", "BEC商务英语"),
    (r"TOEFL", "TOEFL"),
    (r"IELTS", "IELTS"),
    (r"托福", "托福"),
    (r"雅思", "雅思"),
    (r"日语\s*N1", "日语 N1"),
    (r"日语\s*N2", "日语 N2"),
    (r"日语\s*N3", "日语 N3"),
    (r"日语\s*N4", "日语 N4"),
    (r"日语\s*N5", "日语 N5"),
    (r"韩语\s*TOPIK", "韩语 TOPIK"),
    (r"法语\s*(TEF|TCF|DELF|DALF)", r"法语 \1"),
    (r"德语\s*(TestDaF|DSH|Goethe)", r"德语 \1"),
    # Mandarin / Driver
    (r"普通话\s*(一甲|一乙|二甲|二乙|三甲|三乙)", r"普通话\1"),
    (r"机动车\s*驾驶\s*证\s*[ABC]\d", r"机动车驾驶证"),
    (r"驾驶证\s*[ABC]\d", r"机动车驾驶证"),
    (r"\bC1\b", "机动车驾驶证 C1"),
    (r"\bC2\b", "机动车驾驶证 C2"),
    # IT / Professional
    (r"软考\s*(初级|中级|高级)", r"软考\1"),
    (r"计算机\s*等级\s*(一级|二级|三级|四级)", r"NCRE \1"),
    (r"NCRE\s*[1234]", r"NCRE"),
    (r"PMP", "PMP"),
    (r"CFA", "CFA"),
    (r"ACCA", "ACCA"),
    (r"CPA", "CPA"),
    (r"一级建造师", "一级建造师"),
    (r"二级建造师", "二级建造师"),
    (r"教师资格证", "教师资格证"),
    (r"心理咨询师", "心理咨询师"),
    (r"会计从业", "会计从业资格"),
    (r"证券从业", "证券从业资格"),
    (r"基金从业", "基金从业资格"),
    (r"银行从业", "银行从业资格"),
    (r"期货从业", "期货从业资格"),
    (r"华为\s*(HCIA|HCIP|HCIE)", r"华为\1认证"),
    (r"思科\s*(CCNA|CCNP|CCIE)", r"思科\1认证"),
    (r"阿里云\s*(ACA|ACP|ACE)", r"阿里云\1认证"),
    (r"AWS\s*(CLF|SCS|DVA|SAA|SAP|DOP|DEA)", "AWS 认证"),
    (r"腾讯云\s*(TCP|TCE|TCA)", "腾讯云认证"),
    (r"Azure\s*(AZ-900|AZ-104|AZ-305)", "Azure 认证"),
]


def _extract_certificates_by_regex(raw_text: str) -> list[str]:
    """Extract common certificates from raw text using regex patterns.

    Serves as a deterministic fallback when LLM misses certificates.
    """
    import re as _re
    found: set[str] = set()
    for pattern, replacement in _CERTIFICATE_PATTERNS:
        for match in _re.finditer(pattern, raw_text, _re.IGNORECASE):
            cert = _re.sub(pattern, replacement, match.group(0), flags=_re.IGNORECASE)
            found.add(cert.strip())
    return sorted(found)


# ── Per-field supplement extraction prompts ──────────────────────────────────

_PROJECTS_RETRY_PROMPT = """从以下简历文本中提取所有项目经历，返回严格 JSON，不要其他文字。

注意：
1. 提取"项目经历"、"项目经验"、"Projects"板块中的全部内容
2. 包括课程项目、毕业设计、竞赛作品、个人项目、开源项目等
3. 每个项目用一句话或一段简短描述概括
4. 不要遗漏任何项目

返回格式：
{{"projects": ["项目1描述", "项目2描述", "项目3描述"]}}

简历文本：
{resume_text}"""


_INTERNSHIPS_RETRY_PROMPT = """从以下简历文本中提取所有实习/工作经历，返回严格 JSON，不要其他文字。

注意：
1. 提取"实习经历"、"工作经历"、"Internship"、"Work Experience"板块中的全部内容
2. 包括企业实习、兼职、校内助研、实验室实习等
3. 每个实习返回：company（公司/机构名）、role（岗位）、duration（时间）、highlights（核心成果，一句话）
4. 不要遗漏任何实习

返回格式：
{{"internships": [{{"company": "公司名", "role": "岗位", "duration": "时间", "highlights": "成果描述"}}]}}

简历文本：
{resume_text}"""


_CERTIFICATES_RETRY_PROMPT = """从以下简历文本中提取所有证书/资质，返回严格 JSON，不要其他文字。

注意：
1. 提取"证书"、"资质"、"技能证书"、"其他"等板块中的全部内容
2. 包括但不限于：CET-4/6、TOEFL、IELTS、日语 N1/N2、普通话等级、驾驶证、软考、计算机等级、PMP、华为/阿里云/AWS 认证等
3. 一字不落地提取证书名称
4. 不要按"是否与求职相关"过滤

返回格式：
{{"certificates": ["证书1", "证书2", "证书3"]}}

简历文本：
{resume_text}"""


def _supplement_missing_fields(parsed: dict, raw_text: str) -> dict:
    """After primary LLM extraction, supplement any missing fields.

    Uses focused per-field prompts to catch what the main all-in-one prompt missed.
    """
    if not raw_text or len(raw_text) < 50:
        return parsed

    from backend.llm import llm_chat, parse_json_response

    # 0. Job target — if empty, regex fallback (fast & reliable)
    job_target = (parsed.get("job_target") or "").strip()
    if not job_target:
        import re as _re
        jt_patterns = [
            r'(?:求职意向|期望职位|求职目标|意向岗位|期望岗位|目标职位|应聘职位)\s*[：:]\s*([^\n\r]{1,40})',
            r'(?:求职意向|期望职位|求职目标|意向岗位|期望岗位|目标职位|应聘职位)\s+([^\n\r]{1,40})',
        ]
        for pat in jt_patterns:
            m = _re.search(pat, raw_text, _re.IGNORECASE)
            if m:
                jt = m.group(1).strip()
                # Drop trailing punctuation / noise
                jt = _re.sub(r'[\s,，;.；。]+$', '', jt)
                if jt and jt not in {"面议", "不限", "待定", "无", "—", "-", "/"}:
                    parsed["job_target"] = jt
                    logger.info("Job target regex fallback: %s", jt)
                    break

    # 1. Skills — already has retry in _extract_profile_with_llm, skip here

    # 2. Projects — if empty or suspiciously few
    projects = parsed.get("projects", [])
    if len(projects) == 0:
        logger.warning("Primary parse returned 0 projects, running projects supplement")
        try:
            prompt = _PROJECTS_RETRY_PROMPT.format(resume_text=raw_text[:3000])
            result = llm_chat([{"role": "user", "content": prompt}], temperature=0, timeout=30)
            retry_parsed = parse_json_response(result)
            if retry_parsed and isinstance(retry_parsed.get("projects"), list):
                parsed["projects"] = retry_parsed["projects"]
                logger.info("Projects supplement: extracted %d projects", len(retry_parsed["projects"]))
        except Exception as e:
            logger.warning("Projects supplement failed: %s", e)

    # 3. Internships — if empty
    internships = parsed.get("internships", [])
    if len(internships) == 0:
        logger.warning("Primary parse returned 0 internships, running internships supplement")
        try:
            prompt = _INTERNSHIPS_RETRY_PROMPT.format(resume_text=raw_text[:3000])
            result = llm_chat([{"role": "user", "content": prompt}], temperature=0, timeout=30)
            retry_parsed = parse_json_response(result)
            if retry_parsed and retry_parsed.get("internships"):
                # Validate each entry but with relaxed rules (already done in _is_valid_internship)
                valid = []
                for entry in retry_parsed["internships"]:
                    if isinstance(entry, dict) and entry.get("company"):
                        valid.append(entry)
                if valid:
                    parsed["internships"] = valid
                    logger.info("Internships supplement: extracted %d internships", len(valid))
        except Exception as e:
            logger.warning("Internships supplement failed: %s", e)

    # 4. Certificates — regex fallback + LLM supplement
    certificates = parsed.get("certificates", [])
    if len(certificates) == 0:
        # Regex first
        regex_certs = _extract_certificates_by_regex(raw_text)
        if regex_certs:
            parsed["certificates"] = regex_certs
            logger.info("Certificates regex fallback: found %d certs", len(regex_certs))
        # LLM supplement as second chance
        try:
            prompt = _CERTIFICATES_RETRY_PROMPT.format(resume_text=raw_text[:3000])
            result = llm_chat([{"role": "user", "content": prompt}], temperature=0, timeout=30)
            retry_parsed = parse_json_response(result)
            if retry_parsed and retry_parsed.get("certificates"):
                existing = {c.lower() for c in parsed.get("certificates", [])}
                added = 0
                for c in retry_parsed["certificates"]:
                    if c and c.lower() not in existing:
                        parsed.setdefault("certificates", []).append(c)
                        existing.add(c.lower())
                        added += 1
                if added:
                    logger.info("Certificates LLM supplement: added %d certs", added)
        except Exception as e:
            logger.warning("Certificates supplement failed: %s", e)

    return parsed


_SKILLS_RETRY_PROMPT = """从以下简历文本中只提取技能列表，返回严格 JSON，不要其他文字：
{{"skills": [{{"name": "技能名（英文或通用短名）", "level": "familiar"}}]}}

词表仅供参考，不在词表中的技能也必须提取，使用行业通用名称：
{skill_vocab}

简历：{resume_text}"""


def _smart_truncate_resume(text: str, max_chars: int = 4000) -> str:
    """Conservatively truncate resume text to fit LLM prompt limit.

    Strategy: keep head (personal info + education + skills) and tail
    (projects + internships + certificates). Drop low-value middle sections
    (self-evaluation, hobbies) only when necessary.
    """
    if len(text) <= max_chars:
        return text

    import re as _re

    # Section markers to identify boundaries (Chinese + English)
    _SECTION_MARKERS = [
        "专业技能", "技能", "技术栈", "technical skills",
        "项目经历", "项目经验", "projects", "project",
        "实习经历", "实习经验", "工作经历", "work experience", "internship",
        "教育背景", "教育经历", "education",
        "获奖情况", "荣誉", "竞赛", "awards",
        "证书", "资质", "certificates",
        "求职意向", "自我评价", "兴趣爱好", "个人简介",
    ]

    # Build regex that matches any section header at line start
    marker_pattern = _re.compile(
        r'(?:^|\n)\s*(' + '|'.join(_re.escape(m) for m in _SECTION_MARKERS) + r')\s*(?:[：:]|\n)',
        _re.MULTILINE | _re.IGNORECASE
    )

    matches = list(marker_pattern.finditer(text))
    if len(matches) < 3:
        # Can't detect sections — simple head+tail truncation
        head_len = int(max_chars * 0.55)
        tail_len = max_chars - head_len - 20
        return text[:head_len] + "\n...\n" + text[-tail_len:]

    # Mark each section's start position and importance
    section_positions: list[tuple[int, str, int]] = []
    for i, m in enumerate(matches):
        header = m.group(1)
        start = m.start()
        # Determine priority
        pri = 5
        if any(k in header for k in ["专业技能", "技能", "技术栈", "technical skills"]):
            pri = 10
        elif any(k in header for k in ["项目", "project", "实习", "internship", "工作", "work"]):
            pri = 9
        elif any(k in header for k in ["教育", "education"]):
            pri = 8
        elif any(k in header for k in ["获奖", "荣誉", "竞赛", "award", "证书", "certificate"]):
            pri = 7
        elif any(k in header for k in ["求职意向", "期望职位", "目标职位", "应聘职位"]):
            pri = 8  # 求职意向是职业方向的关键信号，必须保留
        elif any(k in header for k in ["自我评价", "兴趣", "个人简介"]):
            pri = 2
        section_positions.append((start, header, pri))

    # Budget allocation: always keep top-priority sections, drop low-priority
    # Sort by priority desc to decide what to include
    sorted_sections = sorted(enumerate(section_positions), key=lambda x: -x[1][2])

    # Determine which sections to include
    budget = max_chars
    # Always reserve space for pre-header text (name, contact)
    pre_header = text[:matches[0].start()] if matches else ""
    pre_header = pre_header[:min(len(pre_header), 600)]  # cap pre-header
    budget -= len(pre_header)

    included: set[int] = set()
    for orig_idx, (start, header, pri) in sorted_sections:
        if orig_idx in included:
            continue
        # Determine section end
        end = section_positions[orig_idx + 1][0] if orig_idx + 1 < len(section_positions) else len(text)
        length = end - start
        if length <= budget:
            included.add(orig_idx)
            budget -= length
        elif pri >= 9 and budget > 200:
            # Critical section: include partial content (actually truncate)
            end = start + budget
            included.add(orig_idx)
            budget = 0
            break
        # Low priority section: skip if over budget

    # If budget remains, greedily add any skipped sections in original order
    if budget > 100:
        for orig_idx, (start, header, pri) in enumerate(section_positions):
            if orig_idx in included:
                continue
            end = section_positions[orig_idx + 1][0] if orig_idx + 1 < len(section_positions) else len(text)
            length = end - start
            if length <= budget:
                included.add(orig_idx)
                budget -= length

    # Build result in original order
    result_parts = [pre_header]
    last_end = len(pre_header)
    for orig_idx in sorted(included):
        start, header, pri = section_positions[orig_idx]
        end = section_positions[orig_idx + 1][0] if orig_idx + 1 < len(section_positions) else len(text)
        # Add ellipsis if there's a gap
        if start > last_end + 10:
            result_parts.append("\n...[内容截断]...\n")
        result_parts.append(text[start:end])
        last_end = end

