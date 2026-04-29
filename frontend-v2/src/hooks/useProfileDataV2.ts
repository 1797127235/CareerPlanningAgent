import { useState, useCallback, useEffect } from 'react'
import { fetchMyProfileV2 } from '@/api/profiles-v2'
import { v2ToV1Profile } from '@/utils/profileAdapter'
import type { V2ProfileData } from '@/types/profile-v2'
import type { ProfileData } from '@/types/profile'

export function useProfileDataV2(enabled = true) {
  const [v2Profile, setV2Profile] = useState<V2ProfileData | null>(null)
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState<string | null>(null)

  const loadProfile = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const v2 = await fetchMyProfileV2()
      setV2Profile(v2)
      setProfile(v2ToV1Profile(v2))
    } catch (err) {
      setError(err instanceof Error ? err.message : '画像加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (enabled) loadProfile()
  }, [enabled, loadProfile])

  return { profile, v2Profile, loading, error, loadProfile }
}
