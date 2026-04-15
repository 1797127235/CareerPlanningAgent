export function sanitizeAiMarkdown(text: string): string {
  return text
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/⭐/g, '')
    .replace(/[💡✅⚠️❌🎯🔥📌]/g, '')
}
