export function parseJdTitle(title: string): { company: string; position: string } {
  const separators = /[—\-·|]/
  const parts = title.split(separators).map((s) => s.trim()).filter(Boolean)
  if (parts.length >= 2) return { company: parts[0], position: parts.slice(1).join(' ') }
  return { company: '', position: title }
}
