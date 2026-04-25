/**
 * Split a narrative blob into 2-3 paragraphs, trying newlines first then
 * sentence-count bucketing. Returns empty if the source is too short.
 */
export function splitParagraphs(
  text: string,
  minSentences = 2,
  maxSentences = 3,
): string[] {
  if (!text || text.trim().length < 10) return []
  const byNewline = text.split(/\n+/).map((s) => s.trim()).filter(Boolean)
  if (byNewline.length >= 2) return byNewline

  const sentences = text.match(/[^。！？.!?]+[。！？.!?]+/g) || [text]
  const out: string[] = []
  let i = 0
  while (i < sentences.length) {
    const size = Math.min(maxSentences, Math.max(minSentences, sentences.length - i))
    out.push(sentences.slice(i, i + size).join('').trim())
    i += size
  }
  return out.filter(Boolean)
}

export function firstSentence(text: string): string {
  const m = text.match(/^[^。！？.!?]+[。！？.!?]?/)
  return m ? m[0].trim() : text.trim()
}
