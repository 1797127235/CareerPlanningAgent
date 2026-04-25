# data/db_30_2_text 文件夹说明

本目录为 **O*NET 30.2 数据库** 的文本版（2026 年 2 月发布），包含职业、技能、教育、工作活动等结构化数据。可用于岗位标准化、技能名规范、职业画像等。

- 官方文档：<https://www.onetcenter.org/dictionary/30.2/text/>
- 许可：Creative Commons Attribution 4.0 International

---

## 一、说明与参考（先看这些）

| 文件名 | 说明 |
|--------|------|
| **Read Me.txt** | 版本说明与官方链接，指明本数据集为 O*NET 30.2、发布月份及文档地址。 |
| **Content Model Reference.txt** | O*NET 内容模型参考：各维度的层级结构（Element ID、名称、描述），如 Abilities、Knowledge、Skills、Work Activities、Tasks 等，用于理解后续各数据文件的 ID 与含义。 |
| **Scales Reference.txt** | 各量表的定义：Scale ID、名称、最小值、最大值（如 Importance 1–5、Level 0–7、Education 类别等），用于解读带数值的表格。 |
| **Level Scale Anchors.txt** | 各量表等级的文字锚点说明，便于把数值解释为「高/中/低」等可读描述。 |

---

## 二、岗位/职业相关（岗位标准化重点）

| 文件名 | 说明 |
|--------|------|
| **Occupation Data.txt** | 职业主表：O*NET-SOC 编码、英文标准职称（Title）、职业描述。是「标准职业」的权威定义，可作岗位归一化的目标。 |
| **Alternate Titles.txt** | 岗位别名表：同一 O*NET-SOC 下的多种英文职称（Alternate Title、Short Title、来源）。**岗位标准化**时可将非标准岗位名映射到 O*NET-SOC。 |
| **Sample of Reported Titles.txt** | 实际报告的岗位名称样本：O*NET-SOC、Reported Job Title、是否在 My Next Move 展示。反映真实招聘/调查中的叫法，可作为别名扩展来源。 |
| **Related Occupations.txt** | 职业间相关关系：O*NET-SOC、相关职业编码、相关程度（Primary-Short / Primary-Long / Supplemental）、序号。用于换岗、推荐相似职业。 |
| **Occupation Level Metadata.txt** | 职业层级元数据，与 O*NET-SOC 的细分层级（如 .00 / .01）相关。 |

---

## 三、技能与知识

| 文件名 | 说明 |
|--------|------|
| **Skills.txt** | 技能数据：按 O*NET-SOC 与 Element ID 给出的技能名称及量表分数（如 Importance、Level 等）。**技能名规范**可参考其中的标准技能名。 |
| **Knowledge.txt** | 知识领域：结构同 Skills，描述职业所需知识及重要程度/水平。 |
| **Abilities.txt** | 能力：认知、体能、感知等能力的 ID 与名称（在 Content Model Reference 中有详细描述）。 |
| **Skills to Work Activities.txt** | 技能 → 工作活动的关联，用于理解技能在具体工作行为中的体现。 |
| **Skills to Work Context.txt** | 技能与工作情境的关联。 |
| **Abilities to Work Activities.txt** | 能力 → 工作活动的关联。 |
| **Abilities to Work Context.txt** | 能力与工作情境的关联。 |
| **Technology Skills.txt** | 技术/软件技能：软件示例、商品代码、是否 Hot Technology、是否 In Demand 等，偏 IT/工具类。 |
| **Tools Used.txt** | 职业使用的工具（设备、软件等）列表。 |

---

## 四、工作活动与任务

| 文件名 | 说明 |
|--------|------|
| **Work Activities.txt** | 工作活动及重要程度/水平：每个职业的「获取信息」「监控过程」等活动及其评分。 |
| **IWA Reference.txt** | 重要工作活动（IWA）参考：Element ID、IWA ID、IWA 标题（简短描述）。 |
| **DWA Reference.txt** | 详细工作活动（DWA）参考：Element ID、IWA ID、DWA ID、DWA 标题，比 IWA 更细。 |
| **Tasks to DWAs.txt** | 任务到 DWA 的映射（若存在），用于任务与标准化工作活动的对应。 |
| **Task Statements.txt** | 任务陈述：O*NET-SOC、Task ID、具体任务描述、任务类型（Core 等）、受访人数等。可直接用于岗位职责/任务画像。 |
| **Task Categories.txt** | 任务分类体系。 |
| **Task Ratings.txt** | 任务的各项评分（如频率、重要性等）。 |
| **Emerging Tasks.txt** | 新兴任务：职业中正在出现或变化的任务，适合做趋势分析。 |

---

## 五、教育、培训与经验

| 文件名 | 说明 |
|--------|------|
| **Education, Training, and Experience.txt** | 按职业的教育/培训/经验要求数据：学历等级、相关工作经验、在职培训等及对应量表分数。 |
| **Education, Training, and Experience Categories.txt** | 教育/经验/培训的类别定义（如学历 1–12、工作经验 1–11、培训类别等），用于解读上一文件的 Category。 |
| **Job Zones.txt** | 职业区域：按所需准备程度划分（1–5 区），含经验、学历、培训、示例职业、SVP 范围等。 |
| **Job Zone Reference.txt** | Job Zone 的简要参考表（与 Job Zones 配套）。 |

---

## 六、兴趣、价值观与工作风格

| 文件名 | 说明 |
|--------|------|
| **Interests.txt** | 职业兴趣：与 Holland RIASEC 六型（现实型、研究型、艺术型、社会型、企业型、传统型）相关的兴趣分数。 |
| **Interests Illustrative Activities.txt** | 与兴趣相关的示例活动。 |
| **Interests Illustrative Occupations.txt** | 与兴趣相关的示例职业。 |
| **Basic Interests to RIASEC.txt** | 基本兴趣到 RIASEC 类型的映射。 |
| **RIASEC Keywords.txt** | RIASEC 类型的关键词。 |
| **Work Values.txt** | 工作价值观：职业对应的内在/外在价值倾向。 |
| **Work Styles.txt** | 工作风格：影响工作表现的个人特质（如成就导向、独立性等）及评分。 |

---

## 七、工作情境

| 文件名 | 说明 |
|--------|------|
| **Work Context.txt** | 工作情境数据：如接触他人程度、自动化程度、决策影响等，按职业与量表给出。 |
| **Work Context Categories.txt** | 工作情境各维度的类别定义，用于解读 Work Context 中的分类值。 |

---

## 八、其他参考

| 文件名 | 说明 |
|--------|------|
| **Survey Booklet Locations.txt** | 与 O*NET 调查手册位置相关的参考信息。 |
| **UNSPSC Reference.txt** | 联合国标准产品与服务代码（UNSPSC）参考，多用于工具/商品分类。 |

---

## 在本项目中的典型用法

- **岗位标准化**：用 `Occupation Data.txt` + `Alternate Titles.txt`（及可选 `Sample of Reported Titles.txt`）建立「别名/非标准岗位名 → O*NET-SOC」；中文侧可继续用 `data/onet_cn_index.json` 做中文关键词 → O*NET。
- **技能名规范**：用 `Skills.txt`、`Technology Skills.txt` 中的标准技能名做同义词/大小写归一；可与 `data/skill_taxonomy.csv` 结合。
- **职业画像 / 推荐**：用 `Related Occupations.txt`、`Task Statements.txt`、`Work Activities.txt`、`Education, Training, and Experience.txt`、`Job Zones.txt` 等做画像或换岗推荐。

以上文件均为制表符分隔的 .txt，首行为表头，编码一般为 UTF-8；读取时注意 O*NET-SOC 与 Element ID 的对应关系可参考 Content Model Reference。
