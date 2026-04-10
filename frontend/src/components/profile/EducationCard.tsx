/* eslint-disable @typescript-eslint/no-explicit-any */
import { motion } from 'framer-motion'
import { GraduationCap, Briefcase } from 'lucide-react'
import type { Education } from '@/types/profile'

interface EducationCardProps {
  education?: Education
  experienceYears?: number
  stagger: number
  cardVariants: any
}

export function EducationCard({ education, experienceYears, stagger, cardVariants }: EducationCardProps) {
  const hasMajor = education?.major && education.major.trim()
  const hasSchool = education?.school && education.school.trim()
  const hasDegree = education?.degree && education.degree.trim()
  const hasExperience = (experienceYears ?? 0) > 0
  const hasEducation = hasMajor || hasSchool || hasDegree

  if (!hasEducation && !hasExperience) return null

  return (
    <motion.div
      custom={1.5 * stagger}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      className="glass p-6"
    >
      <h3 className="text-base font-bold text-slate-900 tracking-tight mb-4">背景信息</h3>

      <div className="space-y-3">
        {hasEducation && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0 mt-0.5">
              <GraduationCap className="w-4 h-4 text-blue-600" />
            </div>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold text-slate-800">
                {[hasDegree && education!.degree, hasMajor && education!.major].filter(Boolean).join(' · ')}
              </div>
              {hasSchool && (
                <div className="text-[12px] text-slate-500 mt-0.5">{education!.school}</div>
              )}
            </div>
          </div>
        )}

        {hasExperience && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center shrink-0 mt-0.5">
              <Briefcase className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold text-slate-800">
                {experienceYears} 年工作经验
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
