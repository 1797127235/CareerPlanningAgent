import { prepare, layout } from '@chenglou/pretext'

/**
 * 二分搜索最大字号使标题刚好 N 行（默认 1 行）
 * @param text 标题文字
 * @param fontFamily 字体 family（例如 "Source Han Serif SC"）
 * @param fontWeight 字重（例如 700）
 * @param maxWidth 容器宽度 px
 * @param maxLines 允许的最大行数
 * @param minSize 最小字号（例如 24）
 * @param maxSize 最大字号（例如 96）
 */
export function fitHeadline(
  text: string,
  fontFamily: string,
  fontWeight: number,
  maxWidth: number,
  maxLines = 1,
  minSize = 24,
  maxSize = 96,
): number {
  let lo = minSize, hi = maxSize, best = minSize
  while (lo <= hi) {
    const mid = Math.floor((lo + hi) / 2)
    const font = `${fontWeight} ${mid}px "${fontFamily}"`
    const prepared = prepare(text, font)
    const { lineCount } = layout(prepared, maxWidth, mid * 1.15)
    if (lineCount <= maxLines) {
      best = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  return best
}
