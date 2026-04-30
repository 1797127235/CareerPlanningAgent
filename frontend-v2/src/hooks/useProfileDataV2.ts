import { useState, useCallback, useEffect } from 'react'
import { fetchMyProfileV2, deleteMyProfileV2 } from '@/api/profiles-v2'
import type { V2ProfileData } from '@/types/profile-v2'

export function useProfileDataV2(enabled = true) {
  const [v2Profile, setV2Profile] = useState<V2ProfileData | null>(null)
  const [source, setSource] = useState<string>('')
  const [updatedAt, setUpdatedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState<string | null>(null)

  const loadProfile = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await fetchMyProfileV2()
      setV2Profile(resp.profile)
      setSource(resp.source)
      setUpdatedAt(resp.updated_at)
    } catch (err) {
      const msg = err instanceof Error ? err.message : '画像加载失败'
      if (msg.includes('用户未创建画像') || msg.includes('404')) {
        setV2Profile(null)
        setSource('')
        setUpdatedAt(null)
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const deleteProfile = useCallback(async () => {
    await deleteMyProfileV2()
    setV2Profile(null)
    setSource('')
    setUpdatedAt(null)
  }, [])

  useEffect(() => {
    if (enabled) loadProfile()
  }, [enabled, loadProfile])

  return { v2Profile, source, updatedAt, loading, error, loadProfile, deleteProfile }
}
