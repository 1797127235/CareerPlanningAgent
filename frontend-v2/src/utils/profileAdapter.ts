import type { V2ProfileData } from '@/types/profile-v2'
import type { ProfileData, Skill } from '@/types/profile'

const LEVEL_MAP: Record<string, Skill['level']> = {
  beginner: 'beginner',
  familiar: 'familiar',
  intermediate: 'proficient',
  advanced: 'expert',
}

export function v2ToV1Profile(v2: V2ProfileData): ProfileData {
  const firstEdu = v2.education[0]

  return {
    id: 0,
    name: v2.name,
    source: 'resume',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    profile: {
      skills: v2.skills.map((s) => ({
        name: s.name,
        level: LEVEL_MAP[s.level] ?? 'familiar',
      })),
      knowledge_areas: [],
      education: firstEdu
        ? {
            degree: firstEdu.degree,
            major: firstEdu.major,
            school: firstEdu.school,
          }
        : undefined,
      experience_years: 0,
      projects: v2.projects.map((p) => p.description || p.name),
      internships: v2.internships.map((i) => ({
        company: i.company,
        role: i.role,
        duration: i.duration,
        tech_stack: i.tech_stack,
        highlights: i.highlights,
      })),
      certificates: v2.certificates,
      soft_skills: {},
    },
    quality: {},
    graph_position: undefined,
    career_goals: undefined,
  }
}
