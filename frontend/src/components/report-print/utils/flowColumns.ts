import {
  prepareWithSegments,
  layoutNextLine,
  type LayoutCursor,
  type PreparedTextWithSegments,
} from '@chenglou/pretext'

/** 矩形障碍物（drop cap / pullquote / 图片 / 侧边卡片 的占位矩形） */
export type RectObstacle = { x: number; y: number; w: number; h: number }

/** 圆形障碍物（editorial engine 的 orb；静态打印大多用不到，保留 API 兼容） */
export type CircleObstacle = {
  cx: number
  cy: number
  r: number
  hPad: number
  vPad: number
}

/** 一列文字区域 */
export type Column = { x: number; y: number; width: number; height: number }

/** 已就位的文字行 */
export type PlacedLine = {
  text: string
  x: number
  y: number
  width: number
}

type Interval = { left: number; right: number }

/** 单区间最小宽度——低于这个就不填字（避免只放下一个字就换行） */
const MIN_SLOT_WIDTH = 50

/**
 * 把 base 区间按 blocked 区间切成若干可用 slot。
 *
 * 这是官方 editorial-engine 的核心原语：一行文字可能被多个障碍物切成左/中/右几段，
 * 每段作为独立 slot 用 layoutNextLine 单独排字，实现"文字同时绕 pullquote 两侧流动"。
 */
function carveTextLineSlots(base: Interval, blocked: Interval[]): Interval[] {
  let slots: Interval[] = [base]
  for (const interval of blocked) {
    const next: Interval[] = []
    for (const slot of slots) {
      if (interval.right <= slot.left || interval.left >= slot.right) {
        next.push(slot)
        continue
      }
      if (interval.left > slot.left) next.push({ left: slot.left, right: interval.left })
      if (interval.right < slot.right) next.push({ left: interval.right, right: slot.right })
    }
    slots = next
  }
  return slots.filter((s) => s.right - s.left >= MIN_SLOT_WIDTH)
}

function circleIntervalForBand(
  cx: number,
  cy: number,
  r: number,
  bandTop: number,
  bandBottom: number,
  hPad: number,
  vPad: number,
): Interval | null {
  const top = bandTop - vPad
  const bottom = bandBottom + vPad
  if (top >= cy + r || bottom <= cy - r) return null
  const minDy = cy >= top && cy <= bottom ? 0 : cy < top ? top - cy : cy - bottom
  if (minDy >= r) return null
  const maxDx = Math.sqrt(r * r - minDy * minDy)
  return { left: cx - maxDx - hPad, right: cx + maxDx + hPad }
}

/**
 * 把一段文字流进单个列内，支持矩形和圆形障碍物。
 * 返回放好的行 + 结束光标（可传给下一列继续流动）。
 *
 * 直接对应官方 editorial-engine.ts::layoutColumn，静态打印用不到动画所以删减。
 */
export function layoutColumn(
  prepared: PreparedTextWithSegments,
  startCursor: LayoutCursor,
  region: Column,
  lineHeight: number,
  rectObstacles: RectObstacle[] = [],
  circleObstacles: CircleObstacle[] = [],
): { lines: PlacedLine[]; cursor: LayoutCursor; endY: number } {
  let cursor: LayoutCursor = startCursor
  let lineTop = region.y
  const lines: PlacedLine[] = []
  let textExhausted = false

  while (lineTop + lineHeight <= region.y + region.height && !textExhausted) {
    const bandTop = lineTop
    const bandBottom = lineTop + lineHeight
    const blocked: Interval[] = []

    for (const c of circleObstacles) {
      const iv = circleIntervalForBand(c.cx, c.cy, c.r, bandTop, bandBottom, c.hPad, c.vPad)
      if (iv !== null) blocked.push(iv)
    }
    for (const r of rectObstacles) {
      if (bandBottom <= r.y || bandTop >= r.y + r.h) continue
      blocked.push({ left: r.x, right: r.x + r.w })
    }

    const slots = carveTextLineSlots({ left: region.x, right: region.x + region.width }, blocked)
    if (slots.length === 0) {
      lineTop += lineHeight
      continue
    }

    // 同一行里按 x 从左到右填入每个 slot
    const ordered = [...slots].sort((a, b) => a.left - b.left)
    for (const slot of ordered) {
      const slotWidth = slot.right - slot.left
      const line = layoutNextLine(prepared, cursor, slotWidth)
      if (line === null) {
        textExhausted = true
        break
      }
      lines.push({
        x: Math.round(slot.left),
        y: Math.round(lineTop),
        text: line.text,
        width: line.width,
      })
      cursor = line.end
    }

    lineTop += lineHeight
  }

  return { lines, cursor, endY: lineTop }
}

/**
 * 便利函数：把文字按顺序流进多列，列间做 cursor handoff。
 * 障碍物仍然是相对"容器"的绝对坐标。返回所有行的数组。
 */
export function flowIntoColumns(
  text: string,
  font: string,
  lineHeight: number,
  columns: Column[],
  rectObstacles: RectObstacle[] = [],
  circleObstacles: CircleObstacle[] = [],
): PlacedLine[] {
  const prepared = prepareWithSegments(text, font)
  const allLines: PlacedLine[] = []
  let cursor: LayoutCursor = { segmentIndex: 0, graphemeIndex: 0 }

  for (const col of columns) {
    const result = layoutColumn(prepared, cursor, col, lineHeight, rectObstacles, circleObstacles)
    allLines.push(...result.lines)
    cursor = result.cursor

    // 如果这一列把文字吃完了，cursor 会停在终点；下一轮 layoutNextLine 返回 null 立即退出
    const probe = layoutNextLine(prepared, cursor, 99999)
    if (probe === null) break
  }
  return allLines
}
