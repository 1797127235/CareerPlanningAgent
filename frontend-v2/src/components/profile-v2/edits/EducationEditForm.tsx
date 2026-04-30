import { useState, useEffect, useRef } from 'react'
import { EditModal, FormField, FormInput, FormSelect, FormRow } from '../EditModal'
import type { V2Education } from '@/types/profile-v2'

interface EducationEditFormProps {
  open: boolean
  onClose: () => void
  data: V2Education
  onSave: (data: V2Education) => Promise<void>
}

export function EducationEditForm({ open, onClose, data, onSave }: EducationEditFormProps) {
  const [school, setSchool] = useState(data.school ?? '')
  const [major, setMajor] = useState(data.major ?? '')
  const [degree, setDegree] = useState(data.degree ?? '本科')
  const [duration, setDuration] = useState(data.duration ?? '')
  const [graduationYear, setGraduationYear] = useState(
    data.graduation_year ? String(data.graduation_year) : ''
  )
  const [saving, setSaving] = useState(false)

  const prevOpenRef = useRef(false)
  useEffect(() => {
    if (open && !prevOpenRef.current) {
      setSchool(data.school ?? '')
      setMajor(data.major ?? '')
      setDegree(data.degree ?? '本科')
      setDuration(data.duration ?? '')
      setGraduationYear(data.graduation_year ? String(data.graduation_year) : '')
    }
    prevOpenRef.current = open
  }, [open, data])

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave({
        school,
        major,
        degree,
        duration,
        graduation_year: graduationYear ? parseInt(graduationYear, 10) : undefined,
      })
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <EditModal
      open={open}
      onClose={onClose}
      title="编辑教育背景"
      onSave={handleSave}
      saving={saving}
    >
      <FormField label="学校名称">
        <FormInput value={school} onChange={setSchool} placeholder="如：清华大学" />
      </FormField>
      <FormField label="专业">
        <FormInput value={major} onChange={setMajor} placeholder="如：计算机科学与技术" />
      </FormField>
      <FormRow>
        <FormField label="学历">
          <FormSelect
            value={degree}
            onChange={setDegree}
            options={[
              { value: '本科', label: '本科' },
              { value: '硕士', label: '硕士' },
              { value: '博士', label: '博士' },
              { value: '大专', label: '大专' },
            ]}
          />
        </FormField>
        <FormField label="毕业年份">
          <FormInput
            value={graduationYear}
            onChange={setGraduationYear}
            placeholder="如：2024"
          />
        </FormField>
      </FormRow>
      <FormField label="在读时间" hint="如：2020.09 - 2024.06">
        <FormInput
          value={duration}
          onChange={setDuration}
          placeholder="如：2020.09 - 2024.06"
        />
      </FormField>
    </EditModal>
  )
}
