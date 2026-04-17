# 功能扩展路线图

> 基于现有系统能力 + 成熟产品调研，按投入产出比排序。
> 每项标注了可复用的现有模块，避免从零构建。

---

## P0 — 必做（演示冲击力最强）

### 1. AI 模拟面试（Mock Interview）

用户选定目标岗位后，LLM 扮演面试官进行多轮模拟面试——自我介绍、行为面试（STAR 法）、技术面试。结束后逐题评分 + 改进建议。

- **参考产品：** VMock SMART Interview、牛客网 AI 面试、Boss 直聘模拟面试
- **可复用：** coach chat SSE 基建、career graph 岗位要求数据、现有 STT/TTS
- **产出：** 独立 `/interview` 页面，`interview_records` 表存储结果

### 2. JD 定制简历（Resume Tailoring per JD）

用户粘贴目标 JD，基于已有 profile + JD 诊断结果，LLM 自动重排经历顺序、调整措辞重点、突出匹配关键词，生成针对该岗位优化的简历版本，支持导出 PDF。

- **参考产品：** Jobscan Resume Optimization、LinkedIn AI Resume Builder、智联招聘智能简历
- **可复用：** `jd_service`、profile 数据、简历解析 prompt
- **产出：** 从"诊断差距"到"帮你填补差距"的完整闭环

### 3. 行业趋势看板（Market Intelligence Dashboard）

将已有 market signal 数据可视化为交互式看板——目标岗位在不同城市的薪资分布、需求热度趋势、核心技能词频变化。

- **参考产品：** Boss 直聘岗位热度图、LinkedIn Salary Insights、前程无忧行业报告
- **可复用：** `market_signal_model.py`、`city_market_signal_model.py`、现有 graph 数据
- **产出：** 数据可视化是竞赛评委最容易被打动的点，已有数据底座只差前端呈现

---

## P1 — 推荐（已有数据基础，扩展自然）

### 4. 多角色对比决策器（Role Comparison Matrix）

选择 2-3 个目标岗位，从薪资、技能匹配度、成长空间、市场需求、学习成本五个维度生成雷达图对比 + LLM 决策建议。

- **参考产品：** CareerExplorer Career Compare、O*NET 岗位对比
- **可复用：** `ComparisonRow.tsx` 雏形、graph 节点数据、market signal
- **产出：** 直击"选哪条路"的核心焦虑

### 5. 智能学习路线图（AI Learning Roadmap）

基于 gap analysis 结果，LLM 自动生成按周/月排列的学习计划——推荐具体课程（MOOC）、书籍、练习项目，标注优先级和预估耗时，可拖拽调整。

- **参考产品：** Roadmap.sh AI 版、牛客网学习路径、实习僧技能提升模块
- **可复用：** action plan 数据、skill gap 分析、career graph 技能要求
- **产出：** action plan 的产品化，从"告诉你缺什么"到"告诉你怎么补"

### 6. AI 职业性格评测（Career Personality Assessment）

LLM 驱动的自适应问答（非固定题库），通过 10-15 个情境题评估职业倾向（类 MBTI/霍兰德但更灵活），结果映射到 Career Graph 推荐匹配角色。

- **参考产品：** CareerExplorer Career Test、实习僧职业测评、PathSource Career Assessment
- **可复用：** `_profiles_sjt.py` SJT 基础、career graph 角色数据
- **产出：** 冷启动利器——新用户无简历时也能获得个性化推荐

### 7. 求职看板增强（Application Kanban + AI Insights）

已有 `JobApplication` 状态流转可视化为看板视图，LLM 自动分析投递转化率，识别"投了很多但面试率低"等模式并给出诊断建议。

- **参考产品：** Huntr、Teal 求职看板、智联招聘投递管理
- **可复用：** `JobApplication` 模型、现有状态枚举（applied → screening → offer/rejected）
- **产出：** 已有数据模型，加看板视图 + AI 分析即为新功能

---

## P2 — 加分项（开发量小，锦上添花）

### 8. AI 职业时间线（Career Timeline Narrative）

基于 profile + Growth Log 数据，LLM 生成"你的职业成长故事"——时间线可视化 + 叙事文本，展示从入学到现在的技能积累、关键转折点、未来预测，可导出精美长图。

- **参考产品：** LinkedIn Year in Review、Spotify Wrapped 职业版
- **可复用：** `narrative.py` 叙事引擎、Growth Log 里程碑数据
- **产出：** 极具演示冲击力，评委一看就懂

### 9. 求职信一键生成（Cover Letter Generator）

结合 JD + 用户 profile，LLM 生成个性化求职信草稿，语气可调（正式/活泼），支持中英双语。

- **参考产品：** Kickresume AI、Rezi AI Cover Letter
- **可复用：** profile 数据、JD 解析结果
- **产出：** 一个 prompt + 一个页面，开发量最小的新功能

### 10. AI 周报自动推送（Career Digest）

基于最近活动（Growth Log 新增记录、求职进展、学习完成情况），LLM 每周自动生成个性化 digest——进展总结、下周建议行动、一条激励语，通过邮件或站内通知推送。

- **参考产品：** LinkedIn Weekly Digest、Notion AI Weekly Summary
- **可复用：** `scheduler.py`、`reminder_service.py`、Growth Log 数据
- **产出：** 体现系统的"主动性"——不只用户来用才有价值，系统主动触达

---

## P3 — 远期探索

### 11. 面试复盘智能分析（Interview Debrief Enhancement）

用户输入面试被问到的问题 + 自己的回答要点，LLM 分析回答质量、给出更优回答示范、识别跨多次面试反复暴露的弱项。

- **可复用：** `InterviewDebrief` 模型、`debrief_service`

### 12. 项目实战推荐（Project Suggestion Engine）

针对技能缺口，LLM 推荐 2-3 个可落地的 side project idea（含技术栈、预计工时、学习目标），帮用户把"学到"变成"做到"。

- **可复用：** skill gap 分析、`ProjectRecord` 模型

### 13. 校友职业路径追踪（Career Path Explorer）

基于 Career Graph 知识图谱，展示"学同专业的前辈们都去了哪些岗位"的桑基图/流向图。

- **可复用：** graph.json 节点/边数据

### 14. 人脉策略建议（Networking Coach）

用户输入目标公司/岗位后，AI Coach 给出 networking 行动建议——社群推荐、cold message 模板、信息面试问题清单。

- **可复用：** coach chat 对话基建

### 15. 价值观-岗位匹配分析

在性格评测基础上增加工作价值观维度（WLB vs 高增长、稳定性 vs 冒险等），LLM 分析用户价值观与目标岗位文化的匹配度。

- **可复用：** SJT 评测框架、career graph 角色数据
