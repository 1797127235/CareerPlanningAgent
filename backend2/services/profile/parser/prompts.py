"""简历解析 prompt 模板，各策略共享使用。"""
from __future__ import annotations

_RESUME_PARSE_PROMPT = """你是一个简历解析 AI。请从以下简历文本中提取结构化信息，以 JSON 格式返回。

返回格式（严格 JSON，不要加注释或 markdown）：
{{
  "name": "姓名（可选）",
  "job_target": "简历中求职意向/期望职位/求职目标/意向岗位原文。查找规则：1) 优先找'求职意向'、'期望职位'、'求职目标'、'意向岗位'、'期望岗位'、'目标职位'、'应聘职位'等板块的内容；2) 如果简历顶部（姓名下方、联系方式附近）有明确的岗位名称，也视为求职意向；3) 完整保留原文（如'项目管理'、'产品经理实习'、'前端开发工程师'）；4) 只写'面议/不限/待定'等模糊词时填空字符串。警告：'项目负责人''技术负责人'是项目经历中的角色描述，不是求职意向，不要误判。{hint_job_target_line}",
  "primary_domain": "此人最主要的技术/职能方向。从以下选一个：AI/LLM开发|后端开发|前端开发|游戏开发|数据工程|系统/基础设施|安全|算法研究|产品设计/PM|其他",
  "career_signals": {{
    "has_publication": true或false（是否有论文发表，包括在投/预印本）,
    "publication_level": "顶会（NeurIPS/ICML/CVPR/ACL/KDD/ICLR等）|CCF-A|CCF-B|CCF-C|无",
    "competition_awards": ["获奖竞赛名称，如Kaggle金牌、数学建模省一等奖"],
    "domain_specialization": "深耕的细分领域，如异常检测、推荐系统、计算机视觉等，无则填空字符串",
    "research_vs_engineering": "research（偏学术/算法创新）|engineering（偏工程落地）|balanced（均衡）",
    "open_source": true或false（是否有开源项目/贡献）,
    "internship_company_tier": "顶级大厂（字节/阿里/腾讯/华为/百度等）|中大厂|初创/中小公司|无"
  }},
  "experience_years": 工作年限数字（在校生/应届生填0）,
  "education": {{"degree": "学位", "major": "专业", "school": "学校"}},
  "skills": [
    {{"name": "技能名称", "level": "advanced|intermediate|familiar|beginner"}}
  ],
  "knowledge_areas": ["知识领域1", "知识领域2"],
  "internships": [
    {{
      "company": "公司名称",
      "role": "实习岗位名称",
      "duration": "时间范围，如2024.10-2024.12",
      "tech_stack": ["技术1", "技术2"],
      "highlights": "核心成果一句话描述，如：优化索引性能提升38%"
    }}
  ],
  "projects": ["项目描述1", "项目描述2"],
  "awards": ["竞赛/荣誉1", "竞赛/荣誉2"],
  "certificates": ["证书名称，必须 100% 完整抽取，见下方规则"]
}}

【技能提取特别要求（严格执行）】
1. 必须完整提取简历中所有明确提到的技术/工具/语言/框架
2. 不要遗漏任何技能：即使只出现一次、即使只是"熟悉"级别，只要简历明确提到使用过，就必须提取
3. 技能名称必须使用简短标准名，不要加"语言/编程/系统/框架/开发"等后缀

【字段分类规则（严格执行）】
- internships：**只放有真实"实习/兼职/校外工作"身份的在职经历**
- projects：所有动手开发/实施的项目，包括个人项目、课程项目、毕设、竞赛作品
- awards：仅放竞赛获奖、荣誉证书、奖学金
- certificates：**一切资质证书**，必须 100% 完整抽取，不得按"是否与求职相关"过滤

技能等级判定规则（严格执行，宁低勿高）：
- advanced：开源贡献/竞赛获奖（省级+）/≥1年工作经验/论文专利
- intermediate：≥2个实质规模项目主要负责人/≥3个月实习经验/省级竞赛获奖
- familiar：课程项目或个人项目中实际使用过
- beginner：学过课程/看过教程，实践经验有限

【子技能继承规则 — 强制执行】
某编程语言的核心特性/子技能，若简历未单独标注熟练度，其等级不得低于该语言本身的等级。

【强制约束 — 应届生/在校生（experience_years=0）】
1. 有实质项目证据的技能可判 intermediate
2. advanced 极少出现，仅限"精通"原词 + 开源/竞赛等硬性成就
3. 证据不足时向下取一档，但有证据时不得人为压低

{skill_vocab}

简历文本：
{resume_text}

只返回 JSON，不要有任何其他文字。"""

_SKILLS_RETRY_PROMPT = """从以下简历文本中只提取技能列表，返回严格 JSON，不要其他文字：
{{"skills": [{{"name": "技能名（英文或通用短名）", "level": "familiar"}}]}}

词表仅供参考，不在词表中的技能也必须提取，使用行业通用名称：
{skill_vocab}

简历：{resume_text}"""

_RESUMESDK_ADAPT_PROMPT = """你是一位简历解析专家。请根据 ResumeSDK 的原始解析结果 + 简历原始文本，生成标准的用户画像 JSON。

【输入 1: ResumeSDK 原始输出】
ResumeSDK 是一个第三方简历解析服务，其输出字段名可能不标准。请根据语义理解每个字段的含义。
常见字段映射参考：
- basic_info → 姓名、年龄、性别等基本信息
- contact → 联系方式（电话、邮箱）
- expect_job → 求职意向/期望职位
- education → 教育背景（学校、专业、学位）
- skills → 技能列表（可能有 skill_name / skill_level 字段）
- work_experience → 工作经历/实习经历
- project_experience → 项目经历
- certificate → 证书
- award → 获奖/荣誉

注意：ResumeSDK 有时会把一个项目拆成多个管理子章节（如"实验论证""质量控制""迭代过程"等），
这些不是真实项目，请过滤掉。真实项目应该有具体的技术实现内容。

ResumeSDK 原始 JSON：
```json
{rs_json}
```

【输入 2: 简历原始文本】
原始文本用于补充 ResumeSDK 遗漏的信息，以及校验 ResumeSDK 的解析结果。

{raw_text}

【输出格式】严格 JSON，不要任何其他文字：
{{
  "name": "姓名",
  "job_target": "求职意向原文，如果没有明确写则填空字符串",
  "primary_domain": "最主要的技术方向，从以下选一个：AI/LLM开发|后端开发|前端开发|游戏开发|数据工程|系统/基础设施|安全|算法研究|嵌入式开发|产品设计/PM|其他",
  "career_signals": {{
    "has_publication": false,
    "publication_level": "无",
    "competition_awards": [],
    "domain_specialization": "",
    "research_vs_engineering": "balanced",
    "open_source": false,
    "internship_company_tier": "无"
  }},
  "experience_years": 0,
  "education": {{"degree": "", "major": "", "school": "", "graduation_year": null}},
  "skills": [{{"name": "技能名", "level": "familiar"}}],
  "knowledge_areas": ["知识领域1", "知识领域2"],
  "internships": [{{"company": "", "role": "", "duration": "", "tech_stack": [], "highlights": ""}}],
  "projects": ["项目描述1", "项目描述2"],
  "awards": ["获奖1"],
  "certificates": ["证书1"]
}}

【关键规则】
1. 项目过滤：只保留有真实技术内容的项目。管理子章节不是项目，必须丢弃。
2. 技能提取：必须完整提取所有技术技能，使用简短标准名。
3. 技能等级：宁低勿高。advanced 需硬性证据；intermediate 需项目证据；familiar 是课程/项目用过；beginner 是学过但实践少。
4. 子技能继承：若 C++ 判为 intermediate，则 STL、智能指针、RAII 等至少也是 intermediate。
5. 技能粒度控制：不要提取编程语言版本号（C++11→C++），不要提取标准库子组件（Vector→STL），不要提取语法特性（Lambda→C++）。
6. 证书：不要遗漏任何证书，包括 CET-4/6、驾驶证、普通话等级、软考等。不要按"与求职相关"过滤。
7. 知识领域：根据技能深度和项目方向推断。
8. internships：只放有真实企业实习身份的经历，个人项目/课程设计不要放这里。

【求职意向特别规则】
- 求职意向必须来自简历中明确的"求职意向/期望职位/目标职位"等板块。
- 项目经历中的角色不是求职意向；实习经历中的岗位是过往经历，不是求职意向。
{hint_job_target_line}
"""
