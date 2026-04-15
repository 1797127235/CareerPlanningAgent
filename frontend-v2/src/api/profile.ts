import { rawFetch } from '@/api/client'

/**
 * 按原文内容匹配更新简历项目描述（不依赖数组下标）。
 * 返回 409 表示原文没匹配到，前端应提示"档案已变动，请刷新"。
 */
export async function refineProfileProject(
  originalText: string,
  newDescription: string,
): Promise<{ ok: boolean }> {
  return rawFetch(`/profiles/me/projects/refine`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      original_text: originalText,
      new_description: newDescription,
    }),
  })
}
