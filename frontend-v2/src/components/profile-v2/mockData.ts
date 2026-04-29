import type { V2ProfileData } from '@/types/profile-v2'

export const mockProfileData: V2ProfileData = {
  name: '小林',
  job_target_text: '后端开发工程师',
  domain_hint: '互联网',
  education: [
    {
      school: '杭州电子科技大学',
      major: '计算机科学与技术',
      degree: '本科',
      duration: '2021.09 - 2025.06',
      graduation_year: 2025,
    },
  ],
  skills: [
    { name: 'Python', level: 'advanced' },
    { name: 'React', level: 'familiar' },
    { name: 'SQL', level: 'familiar' },
    { name: 'LangChain', level: 'beginner' },
  ],
  projects: [
    {
      name: '校园二手交易平台',
      description: '一个帮助校内学生交易闲置物品的微信小程序，负责后端架构和支付对接。',
      tech_stack: ['Node.js', 'MongoDB', '微信小程序'],
      duration: '2024.03 - 2024.06',
      highlights: '独立完成后端 API 设计与数据库建模，支持 500+ 日活用户',
    },
    {
      name: '个人博客系统',
      description: '用 Next.js 搭建的 Markdown 博客，支持暗色模式和 ISR 渲染。',
      tech_stack: ['Next.js', 'TailwindCSS'],
      duration: '2023.10 - 2023.12',
      highlights: '实现 ISR 增量静态再生， Lighthouse 性能评分 95+',
    },
  ],
  internships: [
    {
      company: '某互联网公司',
      role: '后端开发实习生',
      duration: '2024.07 - 2024.09',
      tech_stack: ['Python', 'FastAPI', 'PostgreSQL'],
      highlights: '参与推荐系统接口优化，响应时间下降 30%',
    },
  ],
  awards: ['数学建模省三等奖'],
  certificates: ['CET-6', '普通话二级甲等'],
  raw_text: '',
  dimension_scores: [
    { name: '技术能力', score: 72, source: 'resume' },
    { name: '项目经验', score: 65, source: 'resume' },
    { name: '沟通能力', score: 70, source: 'user_input' },
    { name: '学习能力', score: 85, source: 'user_input' },
  ],
  tags: ['Python', '后端', '应届生', 'FastAPI'],
  strengths: ['算法基础扎实', '有实习经历', '学习能力强'],
  weaknesses: ['无大规模系统经验', '缺少海外背景'],
  constraints: [
    { type: 'location', value: '杭州', label: '杭州' },
    { type: 'location', value: '上海', label: '上海' },
  ],
  preferences: [
    { type: 'industry', value: '互联网', label: '互联网' },
    { type: 'company_size', value: '大厂', label: '大厂' },
    { type: 'growth_speed', value: 'fast', label: '快速晋升' },
  ],
}
