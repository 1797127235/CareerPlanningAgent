import { useState, useRef, useCallback, useEffect } from 'react'
import { parseResume, updateProfile } from '@/api/profiles'

interface UseResumeUploadReturn {
  uploading: boolean
  uploadStep: number
  uploadError: string | null
  justUploaded: boolean
  clearJustUploaded: () => void
  selectedFileName: string
  fileInputRef: React.RefObject<HTMLInputElement | null>
  triggerFileDialog: () => void
  onFileSelected: (e: React.ChangeEvent<HTMLInputElement>) => void
}

let _uploading = false
let _step = 0
let _error: string | null = null
let _justUploaded = false
let _fileName = ''
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
  const [selectedFileName, setSelectedFileName] = useState(_fileName)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const sync = () => {
      setUploading(_uploading)
      setUploadStep(_step)
      setUploadError(_error)
      setJustUploaded(_justUploaded)
      setSelectedFileName(_fileName)
    }
    sync()
    _listeners.add(sync)
    return () => { _listeners.delete(sync) }
  }, [])

  const clearJustUploaded = useCallback(() => {
    _justUploaded = false
    _fileName = ''
    setJustUploaded(false)
    setSelectedFileName('')
  }, [])

  const triggerFileDialog = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const onFileSelected = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return
      e.target.value = ''
      _fileName = file.name
      _listeners.forEach((fn) => fn())
      _set(true, 1, null)
      try {
        _set(true, 2, null)
        const parsed = await parseResume(file)
        _set(true, 3, null)
        await updateProfile({
          profile: { ...parsed.profile, source: 'resume' },
          quality: parsed.quality,
          merge: true,
        })
        _set(false, 0, null)
        await onSuccess()
        _justUploaded = true
        _listeners.forEach((fn) => fn())
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
    selectedFileName,
    fileInputRef,
    triggerFileDialog,
    onFileSelected,
  }
}
