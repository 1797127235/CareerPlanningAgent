import { useState, useRef, useCallback, useEffect } from 'react'
import { parsePreview } from '@/api/profiles-v2'
import type { V2ParsePreviewResponse } from '@/api/profiles-v2'

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
  previewData: V2ParsePreviewResponse | null
  clearPreviewData: () => void
}

let _uploading = false
let _step = 0
let _error: string | null = null
let _justUploaded = false
let _fileName = ''
let _previewData: V2ParsePreviewResponse | null = null
const _listeners = new Set<() => void>()

function _set(uploading: boolean, step: number, error: string | null, justUploaded?: boolean) {
  _uploading = uploading
  _step = step
  _error = error
  if (justUploaded !== undefined) _justUploaded = justUploaded
  _listeners.forEach((fn) => fn())
}

export function useResumeUpload(): UseResumeUploadReturn {
  const [uploading, setUploading] = useState(_uploading)
  const [uploadStep, setUploadStep] = useState(_step)
  const [uploadError, setUploadError] = useState(_error)
  const [justUploaded, setJustUploaded] = useState(_justUploaded)
  const [selectedFileName, setSelectedFileName] = useState(_fileName)
  const [previewData, setPreviewData] = useState<V2ParsePreviewResponse | null>(_previewData)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const sync = () => {
      setUploading(_uploading)
      setUploadStep(_step)
      setUploadError(_error)
      setJustUploaded(_justUploaded)
      setSelectedFileName(_fileName)
      setPreviewData(_previewData)
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

  const clearPreviewData = useCallback(() => {
    _previewData = null
    setPreviewData(null)
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
        const parsed = await parsePreview(file)
        _previewData = parsed
        _set(false, 0, null)
        _justUploaded = true
        _listeners.forEach((fn) => fn())
      } catch (err) {
        _set(false, 0, err instanceof Error ? err.message : '上传失败')
      }
    },
    [],
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
    previewData,
    clearPreviewData,
  }
}
