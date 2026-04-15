import { Chapter } from '@/components/editorial'

export function ProfileEpilogue({
  name,
  sectionsCompleted,
  totalSections,
  updatedAt,
}: {
  name?: string
  sectionsCompleted: number
  totalSections: number
  updatedAt?: string
}) {
  const incomplete = totalSections - sectionsCompleted
  const todos = [
    !name ? '补一个名字' : null,
    sectionsCompleted < 2 ? '补充教育背景' : null,
    sectionsCompleted < 3 ? '加一段实习或项目' : null,
    sectionsCompleted < 4 ? '加几个技能' : null,
    sectionsCompleted < 5 ? '做一次软技能小测' : null,
    sectionsCompleted < 6 ? '选一个目标方向' : null,
  ].filter(Boolean) as string[]

  return (
    <Chapter numeral="" label="">
      <div className="pt-8 border-t border-[var(--line)]">
        {incomplete > 0 && todos.length > 0 && (
          <>
            <h2 className="font-display text-[var(--fs-display-sm)] text-[var(--ink-1)] mb-4">
              还有几件事可以讲 — 但不用现在做完。
            </h2>
            <div className="flex flex-wrap gap-2 mb-8">
              {todos.map((t) => (
                <span
                  key={t}
                  className="px-3 py-1.5 rounded-full text-[12px] font-medium bg-[var(--bg-card)] text-[var(--ink-2)] border border-[var(--line)]"
                >
                  {t}
                </span>
              ))}
            </div>
          </>
        )}
        <p className="font-mono text-[12px] text-[var(--ink-3)]">
          上次更新 {updatedAt ? updatedAt.slice(0, 10) : '—'}
        </p>
        <p className="mt-3 text-[var(--fs-body)] text-[var(--ink-2)] italic">
          这份档案只给你自己和懂你的系统看。
        </p>
      </div>
    </Chapter>
  )
}
