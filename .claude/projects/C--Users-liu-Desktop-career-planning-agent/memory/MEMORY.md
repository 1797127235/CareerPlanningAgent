# Memory Index

## Project
- [project_overview.md](project_overview.md) — 系统整体定位、架构、技术选型与当前进度（截至 2026-03-19）
- [vector_db_architecture.md](project_vector_db.md) — 向量数据库用 Qdrant（默认），ChromaDB 仅保留兼容
- [project_market_signal_pipeline.md](project_market_signal_pipeline.md) — 2026-03-25: 市场信号管线 + 节点扩展 268 + 边 585 + 技能净化
- [project_cs_focus.md](project_cs_focus.md) — 选题限定计算机岗位，非IT节点可清理
- [project_plan_as_home_base.md](project_plan_as_home_base.md) — 2026-03-27: 计划页作为主基地重设计，spec+P1 plan已就绪待执行
- [project_jd_interview_roadmap.md](project_jd_interview_roadmap.md) — 2026-03-28: JD诊断→面试模块路线图，面试模块待JD诊断完成后开发
- [project_real_product.md](project_real_product.md) — 面向真实客户的产品，不是毕设，质量和UX标准要高
- [project_mock_interview_plan.md](project_mock_interview_plan.md) — 2026-04-03: 模拟面试方案——独立SSE+Prompt驱动，不走Agent
- [project_agent_rest_boundary.md](project_agent_rest_boundary.md) — 2026-04-03: Agent/REST职责边界确立，专页走REST，聊天走Agent编排
- [project_graph_rebuild.md](project_graph_rebuild.md) — 2026-04-08: 图谱从developer-roadmap重建，34角色/130边，旧pipeline已删
- [project_applications_module.md](project_applications_module.md) — 2026-04-05: 求职追踪模块现状与 guidance 集成要点
- [project_interview_quality.md](project_interview_quality.md) — 2026-04-06: 面试出题质量低，9个问题已诊断，方案在 docs/plan-g-interview-quality.md 待实现
- [project_profile_next_feature.md](project_profile_next_feature.md) — 下一期：系统推荐岗位 + 适配度随画像动态更新（当前 gap_skills 是冻结快照）

## Feedback
- [feedback_3d_interaction.md](feedback_3d_interaction.md) — 3D 地形图交互体验未完全达到预期，需后续优化
- [feedback_no_excessive_questions.md](feedback_no_excessive_questions.md) — 先回答核心问题，不要在回答前堆砌澄清问题
- [feedback_3d_visual_tuning.md](feedback_3d_visual_tuning.md) — 3D视觉调参用户更擅长，Claude专注架构重构，不反复猜参数
- [feedback_audit_before_implement.md](feedback_audit_before_implement.md) — 方案先审查再实现，不要急于上手；冷启动/域迁移等问题要提前发现
- [feedback_integrate_not_pile.md](feedback_integrate_not_pile.md) — 功能要串联成整体体验，不要堆孤岛模块
- [feedback_flow_first.md](feedback_flow_first.md) — 先理清用户流程再写代码，不要一上来就堆接口和基础设施
- [feedback_listen_first.md](feedback_listen_first.md) — 用户给了参考/明确指令时直接执行，连续失败两次立即停下问方向
- [feedback_think_before_follow.md](feedback_think_before_follow.md) — 设计决策要有自己的判断，不要被质疑就立刻改，也不要拍脑袋选完说不出理由
- [feedback_design_style.md](feedback_design_style.md) — 全站SaaS简洁风+图谱页3D沉浸暗色，赛博朋克已放弃
- [feedback_code_quality.md](feedback_code_quality.md) — 写代码不能让现有代码变乱，保持整洁一致性
- [feedback_verify_before_claiming.md](feedback_verify_before_claiming.md) — 声称"已经是X"前追踪完整数据链路到渲染层，不要只靠推理
- [feedback_homepage_layout.md](feedback_homepage_layout.md) — 首页 returning user 用 sticky 画像栏+内容区，不要 hero 大字动画（已验证）
- [feedback_no_code_without_permission.md](feedback_no_code_without_permission.md) — 未经用户明确许可不写代码，只分析回答，等确认再动手
