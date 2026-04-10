/** Score → Tailwind text color class */
export function scoreColor(score: number): string {
  if (score <= 30) return 'text-red-500'
  if (score <= 70) return 'text-yellow-600'
  return 'text-green-600'
}

/** Normalize a datetime string to UTC so JS parses it correctly.
 *  SQLite returns naive datetimes (no timezone indicator); without this
 *  fix, new Date("2026-04-06T10:30:00") is treated as local time,
 *  causing an 8-hour offset for users in UTC+8. */
function toUtcDate(dateStr: string): Date {
  const s = /Z|[+-]\d{2}:?\d{2}$/.test(dateStr) ? dateStr : dateStr + 'Z'
  return new Date(s)
}

/** Date string → compact display (M/D HH:MM) */
export function formatDate(dateStr: string): string {
  try {
    const d = toUtcDate(dateStr)
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  } catch {
    return dateStr
  }
}
