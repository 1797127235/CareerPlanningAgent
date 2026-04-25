import { Upload, PenLine } from 'lucide-react'
import { UploadCta } from './UploadCta'

export function ProfilePrologue({
  hasProfile,
  name,
  createdAt,
  updatedAt,
  uploading,
  uploadStep,
  uploadError,
  onUpload,
  onManual,
}: {
  hasProfile: boolean
  name?: string
  createdAt?: string
  updatedAt?: string
  uploading: boolean
  uploadStep: number
  uploadError: string | null
  onUpload: () => void
  onManual: () => void
}) {
  const daysSince = createdAt
    ? Math.max(1, Math.floor((Date.now() - new Date(createdAt).getTime()) / (1000 * 60 * 60 * 24)))
    : 1

  return (
    <section className="pt-16 md:pt-24 pb-8">
      <p className="font-sans text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--chestnut)] mb-3">
        Open File · 你的档案
      </p>
      {hasProfile ? (
        <>
          <h1 className="font-display font-medium text-[length:var(--fs-display-xl)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight max-w-[22ch]">
            我们已经认识 {daysSince} 天了。
            <br />
            最近更新的是 {updatedAt ? updatedAt.slice(0, 10) : '今天'}。
          </h1>
          <p className="mt-6 font-sans text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] max-w-[68ch]">
            下面是你之前讲给系统听的，随时可以补。这份档案只给你自己和懂你的系统看，不会给任何第三方。
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button
              onClick={onUpload}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] border border-[var(--line)] hover:bg-[var(--line)]/10 transition-colors"
            >
              <Upload className="w-4 h-4" /> 重新上传简历
            </button>
            <button
              onClick={onManual}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-[13px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] transition-colors"
            >
              <PenLine className="w-4 h-4" /> 手动补一笔
            </button>
          </div>
        </>
      ) : (
        <>
          <h1 className="font-display font-medium text-[length:var(--fs-display-xl)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight max-w-[22ch]">
            还没开始讲给我听。
            <br />
            一份简历，或者几句话，都行。
          </h1>
          <p className="mt-6 font-sans text-[length:var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)] max-w-[68ch]">
            这份档案只给系统看，不会给任何第三方。你可以传一份简历让系统自动提取，也可以先手动填几句，以后随时补。
          </p>
          <div className="mt-10 space-y-4 max-w-md">
            <UploadCta
              step={uploadStep}
              label="上传一份简历"
              subLabel="PDF / Word / TXT，10MB 以内"
              onClick={onUpload}
            />
            {uploadError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
                {uploadError}
              </div>
            )}
            <button
              onClick={onManual}
              className="w-full text-left rounded-xl border border-[var(--line)] bg-[var(--bg-card)] px-6 py-5 hover:shadow-[var(--shadow-paper)] transition-shadow"
            >
              <p className="font-sans text-[length:var(--fs-body-lg)] font-medium text-[var(--ink-1)]">
                手动讲给我听
              </p>
              <p className="text-[length:var(--fs-body)] text-[var(--ink-2)]">
                几个字就够了，不用一次填完
              </p>
            </button>
          </div>
        </>
      )}
    </section>
  )
}
