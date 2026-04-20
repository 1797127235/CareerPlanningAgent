import { useState, useCallback, useEffect } from 'react'
import { apiFetch } from '@/api/client'
import { fetchProfile, updateProfile } from '@/api/profiles'
import type { ProfileData } from '@/types/profile'
import type { ManualProfilePayload } from '@/components/profile'

interface UseProfileDataReturn {
  profile: ProfileData | null
  loading: boolean
  loadError: string | null
  loadProfile: () => Promise<void>

  /* actions */
  reparsing: boolean
  handleReparse: () => Promise<void>
  deleteConfirm: boolean
  setDeleteConfirm: (v: boolean) => void
  handleDelete: () => Promise<void>

  /* edit */
  savingEdit: boolean
  handleSaveEdit: (data: ManualProfilePayload) => Promise<void>

  /* shared error */
  actionError: string | null
}

export function useProfileData(token: string | null): UseProfileDataReturn {
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [reparsing, setReparsing] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [savingEdit, setSavingEdit] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const [loadError, setLoadError] = useState<string | null>(null)

  const loadProfile = useCallback(async () => {
    if (!token) { setLoading(false); return }
    setLoading(true)
    setLoadError(null)
    try {
      const data = await fetchProfile()
      setProfile(data)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : '画像加载失败，请刷新重试')
    }
    setLoading(false)
  }, [token])

  useEffect(() => {
    loadProfile()
  }, [loadProfile])

  const handleReparse = useCallback(async () => {
    setReparsing(true)
    setActionError(null)
    try {
      const res = await apiFetch('/profiles/reparse', { method: 'POST' })
      if (res.success) {
        await loadProfile()
      } else {
        setActionError((res as { message?: string }).message || '重新解析失败')
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '重新解析失败')
    } finally {
      setReparsing(false)
    }
  }, [loadProfile])

  const handleDelete = useCallback(async () => {
    try {
      await apiFetch('/profiles', { method: 'DELETE' })
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '删除失败')
      setDeleteConfirm(false)
      return
    }
    setDeleteConfirm(false)
    // Load after confirmed delete — failure here just means stale UI, not a delete failure
    await loadProfile().catch(() => { setProfile(null) })
  }, [loadProfile])

  const handleSaveEdit = useCallback(async (data: ManualProfilePayload) => {
    setSavingEdit(true)
    setActionError(null)
    try {
      // Preserve existing fields not exposed by ManualProfilePayload
      // (soft_skills, career_signals, primary_domain, raw_text 等)
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
  }, [loadProfile, profile])

  return {
    profile,
    loading,
    loadError,
    loadProfile,
    reparsing,
    handleReparse,
    deleteConfirm,
    setDeleteConfirm,
    handleDelete,
    savingEdit,
    handleSaveEdit,
    actionError,
  }
}
