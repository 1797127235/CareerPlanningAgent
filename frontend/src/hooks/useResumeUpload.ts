import { useState, useRef, useCallback, useEffect } from 'react'
import { apiFetch, apiUpload } from '@/api/client'
import { fetchProfile } from '@/api/profiles'

interface UseResumeUploadReturn {
  uploading: boolean
  uploadStep: number
  uploadError: string | null
  justUploaded: boolean
  clearJustUploaded: () => void
  fileInputRef: React.RefObject<HTMLInputElement | null>
  triggerFileDialog: () => void
  onFileSelected: (e: React.ChangeEvent<HTMLInputElement>) => void
}

/* ── Module-level upload state (survives unmount/remount) ── */
let _uploading = false
let _step = 0
let _error: string | null = null
let _justUploaded = false
const _listeners = new Set<() => void>()

function _set(uploading: boolean, step: number, error: string | null, justUploaded?: boolean) {
  _uploading = uploading
  _step = step
  _error = error
  if (justUploaded !== undefined) _justUploaded = justUploaded
  _listeners.forEach((fn) => fn())
}

export function useResumeUpload(onSuccess: () => Promise<void>): UseResumeUploadReturn {
  const [uploading, setUploading] = useState(_uploading)
  const [uploadStep, setUploadStep] = useState(_step)
  const [uploadError, setUploadError] = useState(_error)
  const [justUploaded, setJustUploaded] = useState(_justUploaded)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const sync = () => {
      setUploading(_uploading)
      setUploadStep(_step)
      setUploadError(_error)
      setJustUploaded(_justUploaded)
    }
    sync()
    _listeners.add(sync)
    return () => { _listeners.delete(sync) }
  }, [])

  const clearJustUploaded = useCallback(() => {
    _justUploaded = false
    setJustUploaded(false)
  }, [])

  const triggerFileDialog = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const onFileSelected = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return
      e.target.value = ''

      _set(true, 1, null)
      try {
        // Step 1: parse resume via LLM
        _set(true, 2, null)
        const parseRes = await apiUpload<{
          profile: Record<string, unknown>
          quality: Record<string, unknown>
        }>('/profiles/parse-resume', file)
        if (!parseRes.success || !parseRes.data) {
          _set(false, 0, parseRes.message || '简历解析失败')
          return
        }

        // Step 2: ask user whether to replace or append, if the profile already
        // has meaningful content. First upload → straight replace (skip dialog).
        let shouldMerge = false
        try {
          const existing = await fetchProfile()
          const hasExistingContent =
            (existing?.skills?.length ?? 0) > 0 ||
            (existing?.projects?.length ?? 0) > 0
          if (hasExistingContent) {
            shouldMerge = window.confirm(
              '已有简历内容。\n\n确定 = 把新简历追加（合并进现有档案，旧项目保留）\n取消 = 用新简历替换（删除现有档案内容）',
            )
          }
        } catch {
          // if we can't read existing profile, default to replace (safe option)
          shouldMerge = false
        }

        _set(true, 3, null)
        const saveRes = await apiFetch('/profiles', {
          method: 'PUT',
          body: JSON.stringify({
            profile: { ...parseRes.data.profile, source: 'resume' },
            quality: parseRes.data.quality,
            merge: shouldMerge,
          }),
        })
        if (!saveRes.success) {
          _set(false, 0, (saveRes as { message?: string }).message || '画像保存失败')
          return
        }

        _set(false, 0, null)
        await onSuccess()
        // Set justUploaded AFTER loadProfile completes so dialog gets fresh data
        _justUploaded = true
        _listeners.forEach(fn => fn())
        // Coach notification dispatched by the calling component after profile loads
        // (so it can include actual profile data for a personalized greeting)
      } catch (err) {
        _set(false, 0, err instanceof Error ? err.message : '上传失败')
      }
    },
    [onSuccess],
  )

  return {
    uploading,
    uploadStep,
    uploadError,
    justUploaded,
    clearJustUploaded,
    fileInputRef,
    triggerFileDialog,
    onFileSelected,
  }
}

/**
 * Lightweight hook for Layout to observe justUploaded state
 * without needing the full upload machinery.
 */
export function useJustUploaded() {
  const [justUploaded, setJustUploaded] = useState(_justUploaded)

  useEffect(() => {
    const sync = () => setJustUploaded(_justUploaded)
    _listeners.add(sync)
    return () => { _listeners.delete(sync) }
  }, [])

  const clear = useCallback(() => {
    _justUploaded = false
    setJustUploaded(false)
    _listeners.forEach(fn => fn())
  }, [])

  return { justUploaded, clearJustUploaded: clear }
}
