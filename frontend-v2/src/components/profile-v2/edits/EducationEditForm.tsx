import { useState } from 'react'
import { EditModal, FormField, FormInput, FormSelect, FormRow } from '../EditModal'
import type { Education } from '@/types/profile'

interface EducationEditFormProps {
  open: boolean
  onClose: () => void
  data: Education
  onSave: (data: Education) => Promise<void>
}

export function EducationEditForm({ open, onClose, data, onSave }: EducationEditFormProps) {
  const [school, setSchool] = useState(data.school ?? '')
  const [major, setMajor] = useState(data.major ?? '')
  const [degree, setDegree] = useState(data.degree ?? '本科')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave({ school, major, degree })
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
      </FormRow>
    </EditModal>
  )
}
