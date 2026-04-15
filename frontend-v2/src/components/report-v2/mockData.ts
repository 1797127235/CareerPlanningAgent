import type { ReportV2Data } from '@/api/report'

export const mockReportData: ReportV2Data = {
  version: '1.0',
  report_type: 'long',
  student: { user_id: 1, profile_id: 1 },
  target: { node_id: 'cpp_backend', label: '系统 C++ 工程师', zone: '技术' },
  match_score: 68,
  four_dim: {
    foundation: 72,
    skills: 64,
    qualities: null,
    potential: 70,
  },
  narrative:
    '你像一个被工程问题吸引的人 — 喜欢把混乱变成秩序。\n' +
    '你的项目里反复出现“性能”“并发”“稳定性”这些关键词，说明你对系统底层有天然的好奇心。' +
    '简历中提到的「基于 epoll 的高并发网络库」是一个不错的切入点，它展示了你能独立处理复杂工程问题的意愿。' +
    '不过，项目描述目前还停留在“实现了什么功能”的层面，缺少 QPS、延迟、压测数据等可量化的成果。' +
    '如果你能在下一次迭代中补上一组 wrk 压测结果和对比数据，这段经历的说服力会提升一个档次。',
  diagnosis: [
    {
      source: '基于 epoll 的高并发网络库',
      source_type: 'resume',
      source_id: 0,
      current_text:
        '实现了一个基于 epoll 的高并发网络库，支持百万级连接，优化了事件循环逻辑，降低了延迟。',
      status: 'pass',
      highlight: '展示了独立完成系统级组件的能力',
      issues: [],
      suggestion: '',
    },
    {
      source: '个人博客系统',
      source_type: 'resume',
      source_id: 1,
      current_text: '使用 Vue + Spring Boot 开发了一个个人博客系统，实现了文章发布和评论功能。',
      status: 'needs_improvement',
      highlight: '有完整前后端分离的实践经验',
      issues: ['缺少量化数据'],
      suggestion: '补充日活用户数、接口响应时间、数据库查询优化前后的对比数据。',
    },
  ],
  market: {
    demand_change_pct: 12,
    salary_cagr: 8,
    salary_p50: 350000,
    timing: 'good',
    timing_label: '良好',
  },
  skill_gap: {
    core: { total: 5, matched: 3, pct: 60, practiced_count: 2, claimed_count: 1 },
    important: { total: 8, matched: 5, pct: 62, practiced_count: 3, claimed_count: 2 },
    bonus: { total: 4, matched: 1, pct: 25, practiced_count: 0, claimed_count: 1 },
    top_missing: [
      { name: 'Linux 内核网络栈', freq: 0.85, tier: 'core', covered_by_project: false, fill_path: 'learn' },
      { name: '分布式一致性', freq: 0.72, tier: 'important', covered_by_project: false, fill_path: 'practice' },
      { name: '性能 profiling', freq: 0.68, tier: 'important', covered_by_project: true, fill_path: 'both' },
    ],
    matched_skills: [
      { name: 'C++', tier: 'core', status: 'practiced', freq: 0.95 },
      { name: 'epoll', tier: 'core', status: 'practiced', freq: 0.88 },
      { name: '多线程', tier: 'core', status: 'practiced', freq: 0.9 },
      { name: 'Redis', tier: 'important', status: 'claimed', freq: 0.75 },
    ],
    has_project_data: true,
  },
  growth_curve: [
    { date: '01/10', score: 55 },
    { date: '02/15', score: 60 },
    { date: '03/20', score: 64 },
    { date: '04/10', score: 68 },
  ],
  action_plan: {
    stages: [
      {
        stage: 1,
        label: '立即整理',
        duration: '0-2周',
        milestone: '简历更新完成',
        items: [
          {
            id: 'prep_resume',
            type: 'job_prep',
            text: '完善简历：建议突出与系统 C++ 工程师相关的技术关键词和可量化成果，让面试官在 10 秒内看到你的工程价值。',
            tag: '求职必备',
            priority: 'high',
            done: false,
            phase: 1,
            deliverable: '更新后的简历 PDF',
          },
          {
            id: 'prep_apply',
            type: 'job_prep',
            text: '已投 0 家，建立目标公司候选列表（5-10家），区分保底/目标/冲刺三档。',
            tag: '尚未开始投递',
            priority: 'medium',
            done: false,
            phase: 1,
            deliverable: '投递记录',
          },
        ],
      },
      {
        stage: 2,
        label: '技能补强',
        duration: '2-6周',
        milestone: '补齐核心技能缺口',
        items: [
          {
            id: 'skill_linux',
            type: 'skill',
            sub_type: 'learn',
            text: '当前项目描述中未见 Linux 内核网络栈相关的具体技术关键词，建议关注该方向在目标岗位中的实践形态和面试考察点。',
            tag: '面试追问点',
            skill_name: 'Linux 内核网络栈',
            priority: 'high',
            done: false,
            phase: 2,
            deliverable: '学习笔记 + demo',
          },
        ],
      },
      {
        stage: 3,
        label: '项目冲刺+求职',
        duration: '6-12周',
        milestone: '项目推上 GitHub',
        items: [
          {
            id: 'proj_main',
            type: 'project',
            text: '当前项目描述偏向“做了什么”，而缺少“做成了什么”的量化叙事。补写 README 和性能测试后推送 GitHub。',
            tag: '可量化缺失',
            priority: 'high',
            done: false,
            phase: 3,
            deliverable: 'GitHub 仓库链接',
          },
        ],
      },
    ],
    skills: [
      {
        id: 'skill_linux',
        type: 'skill',
        sub_type: 'learn',
        text: '当前项目描述中未见 Linux 内核网络栈相关的具体技术关键词，建议关注该方向在目标岗位中的实践形态和面试考察点。',
        tag: '面试追问点',
        skill_name: 'Linux 内核网络栈',
        priority: 'high',
        done: false,
      },
    ],
    project: [
      {
        id: 'proj_main',
        type: 'project',
        text: '当前项目描述偏向“做了什么”，而缺少“做成了什么”的量化叙事。补写 README 和性能测试后推送 GitHub。',
        tag: '可量化缺失',
        priority: 'high',
        done: false,
      },
    ],
    job_prep: [
      {
        id: 'prep_resume',
        type: 'job_prep',
        text: '完善简历：建议突出与系统 C++ 工程师相关的技术关键词和可量化成果。',
        tag: '求职必备',
        priority: 'high',
        done: false,
      },
      {
        id: 'prep_apply',
        type: 'job_prep',
        text: '已投 0 家，建立目标公司候选列表（5-10家），区分保底/目标/冲刺三档。',
        tag: '尚未开始投递',
        priority: 'medium',
        done: false,
      },
    ],
  },
  delta: {
    prev_score: 62,
    score_change: 6,
    prev_date: '2026-03-15T10:00:00+00:00',
    gained_skills: ['epoll', '多线程'],
    still_missing: ['Linux 内核网络栈', '分布式一致性', '性能 profiling'],
    plan_progress: { done: 0, total: 5 },
    next_action: '完善简历：建议突出与系统 C++ 工程师相关的技术关键词和可量化成果。',
  },
  soft_skills: {},
  career_alignment: {
    observations:
      '基于当前档案标签，可初步观察与目标岗位的技能重叠情况。C++ 和并发编程已经有项目实证，但分布式系统和底层网络协议仍缺少直接证据。',
    alignments: [
      {
        node_id: 'cpp_backend',
        label: '系统 C++ 工程师',
        score: 0.68,
        evidence: '用户已标定该方向为目标岗位，项目中有 epoll 和高并发相关实践。',
        gap: '建议补充内核网络、性能 profiling 和分布式一致性相关的学习或项目产出。',
      },
      {
        node_id: 'go_backend',
        label: 'Go 后端开发',
        score: 0.55,
        evidence: '并发模型和工程能力可以迁移，但语言栈差异需要额外学习成本。',
        gap: '需要补充 Go 语言生态、GMP 模型和常见中间件实践经验。',
      },
    ],
    cannot_judge: ['晋升节奏', '团队匹配度'],
  },
  differentiation_advice:
    '在系统 C++ 方向，差异化来自于“能把性能数字讲清楚”和“能定位到底层瓶颈”。',
  ai_impact_narrative:
    '这个方向的日常是面对复杂的工程约束，写出稳定、可维护且高性能的代码。不是追逐最新框架，而是深入理解系统行为。',
  project_recommendations: [],
  project_mismatch: false,
  generated_at: '2026-04-15T11:15:00+00:00',
}
