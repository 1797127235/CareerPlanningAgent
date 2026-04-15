import type { CoachResultDetail } from '@/types/coach'

export const mockJdDiagnosis: CoachResultDetail = {
  id: 101,
  result_type: 'jd_diagnosis',
  title: 'Bytedance · 后端开发工程师',
  summary: '匹配度 68%，具备 3 项核心技能，还有 4 项缺口待补齐。',
  detail: {
    _structured: true,
    match_score: 68,
    matched_skills: ['Go', 'Redis', 'MySQL'],
    gap_skills: [
      { skill: '分布式事务', priority: 'high', match_delta: 0 },
      { skill: 'Kubernetes', priority: 'high', match_delta: 0 },
      { skill: 'Kafka', priority: 'medium', match_delta: 0 },
      { skill: '微服务治理', priority: 'low', match_delta: 0 },
    ],
    jd_title: 'Bytedance · 后端开发工程师',
    company: 'Bytedance',
    job_url: 'https://jobs.bytedance.com/example',
  },
  metadata: { match_score: 68 },
  created_at: '2025-01-10T08:00:00Z',
}

export const mockCareerReport: CoachResultDetail = {
  id: 102,
  result_type: 'career_report',
  title: '前端工程师 · 职业发展报告',
  summary: '基于你的画像和市场需求，整理出未来 1-3 年的职业路径建议。',
  detail: {
    _structured: false,
    raw_text:
`## 现状概览

你目前的基础扎实，React 与 TypeScript 是核心优势。市场数据显示，中级前端岗位在过去一年需求稳定，但高级岗位更青睐具备工程化与全栈视野的候选人。

## 三条可行路径

- **深耕前端工程化**：构建系统、性能优化、DevOps 协同。
- **横向扩展全栈**：补 Node.js / 数据库 / 云原生部署能力。
- **转向产品技术型角色**：结合用户体验思维，走技术产品专家路线。

## 建议时间表

| 阶段 | 时间 | 关键动作 |
|------|------|----------|
| 短期 | 0-6 个月 | 补全工程化工具链（Vite、CI/CD） |
| 中期 | 6-18 个月 | 主导一个完整项目的技术方案设计 |
| 长期 | 18-36 个月 | 建立跨团队技术影响力 |

> 职业发展不是单行道，而是根据市场信号不断微调方向的动态过程。`,
  },
  metadata: {},
  created_at: '2025-01-12T10:30:00Z',
}

export const mockInterviewReview: CoachResultDetail = {
  id: 103,
  result_type: 'interview_review',
  title: '蚂蚁集团 · 前端一面复盘',
  summary: '整体表现中等偏上，技术深度足够，但项目叙述的结构性可以更强。',
  detail: {
    _structured: false,
    raw_text:
`## 亮点

- 对 React 并发机制的理解准确，能结合源码解释。
- 性能优化案例有数据支撑，说服力不错。

## 可以改进的地方

- 项目背景交代过长，建议用「情境 → 行动 → 结果」压缩到 90 秒内。
- 遇到不会的问题时，可以先给出近似思路，再坦诚说明不熟悉细节。

> "面试不是答题比赛，而是一次双向的沟通。",`,
  },
  metadata: {},
  created_at: '2025-01-14T14:00:00Z',
}
