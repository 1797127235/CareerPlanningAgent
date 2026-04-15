import { useState, useCallback, useEffect } from 'react'
import { fetchProfile, updateProfile, resetProfile } from '@/api/profiles'
import type { ProfileData } from '@/types/profile'

export interface ManualProfilePayload {
  name: string
  education: { degree: string; major: string; school: string }
  experience_years: number
  job_target: string
  skills: Array<{ name: string; level: string }>
  knowledge_areas: string[]
  projects: Array<string | Record<string, unknown>>
  internships: Array<Record<string, unknown>>
  certificates: string[]
  awards: string[]
}

export function useProfileData(enabled = true) {
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [savingEdit, setSavingEdit] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const loadProfile = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const data = await fetchProfile()
      setProfile(data)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : '画像加载失败，请刷新重试')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (enabled) loadProfile()
  }, [enabled, loadProfile])

  const handleSaveEdit = useCallback(async (data: ManualProfilePayload) => {
    setSavingEdit(true)
    setActionError(null)
    try {
      const existing = profile?.profile ?? {}
      await updateProfile({
        profile: {
          ...existing,
          name: data.name,
          skills: data.skills,
          knowledge_areas: data.knowledge_areas,
          education: data.education,
          experience_years: data.experience_years,
          job_target: data.job_target,
          projects: data.projects,
          internships: data.internships,
          certificates: data.certificates,
          awards: data.awards,
        },
        quality: null,
      })
      await loadProfile()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '更新失败')
    } finally {
      setSavingEdit(false)
    }
  }, [profile, loadProfile])

  const handleDelete = useCallback(async () => {
    try {
      await resetProfile()
      await loadProfile()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '删除失败')
    }
  }, [loadProfile])

  return {
    profile,
    loading,
    loadError,
    loadProfile,
    savingEdit,
    handleSaveEdit,
    handleDelete,
    actionError,
  }
}
