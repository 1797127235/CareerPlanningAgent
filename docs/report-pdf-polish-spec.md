# Report PDF Polish Spec

> 针对打印版报告（`frontend/src/components/report-print`）在 PDF 输出中的排版缺陷，进行一轮 P0/P1 修复。  
> **根因补充**：Chapter II 的 pullquote 文字叠压问题，是因为早期 `flowColumns.ts` 概念代码只算单 slot；真实算法需按 Pretext 官方 `editorial-engine.ts` 的 `layoutColumn + carveTextLineSlots` 重写——把一行切成多个 slot 分别填字。该文件已重写完毕，以下 5 点为基于正确排版引擎的后续修复。

---

## P0-1 · Chapter I 大标题字号过大 + 顶部留白异常

**问题**  
Chapter I 的大标题在打印页中字号过大，导致溢出或挤压；同时顶部存在写死的空白偏移，视觉不紧凑。

**修复方案**
1. `PrintHeader` 组件里，`fitHeadline` 的 `maxSize` 从当前值降到 **56**。
2. `PrintChapterI` 中所有写死的 `height` / `offset` 值去掉，改为基于内容自适应或容器比例计算，消除死空白。

---

## P0-2 · Chapter II alignments 卡片被截断

**问题**  
Chapter II 的 alignments grid 卡片在窄列或跨列场景下，内容被截断，label 和 evidence 撑破容器。

**修复方案**
- 给 grid 内的卡片容器加：
  - `min-w-0`
  - `overflow-hidden`
- label 文本加 `truncate`（单行截断 + 省略号）。
- evidence 文本加 `line-clamp-4`（最多 4 行，超出折叠），防止长 evidence 把卡片撑爆。

---

## P0-3 · Chapter II pullquote 与正文叠压

**问题**  
Pullquote 区域与环绕正文发生文字叠压。

**修复方案**
1. 利用 Pretext 的排版能力，**先计算 pullquote 内容的真实高度**。
2. 将该高度生成一个 **RectObstacle**，传入 `flowColumns.ts` 的 `layoutColumn`。
3. 同一个 rect **同时充当视觉渲染盒**（pullquote 的边框/背景）和 **排版障碍物**，确保正文自动绕排，不再叠压。

---

## P1-1 · Chapter III 侧边色条

**问题**  
Chapter III 的某些卡片/模块带有左侧彩色边条（`border-l-*`），与 impeccable 视觉规范冲突。

**修复方案**
- 在 `report-print` 范围内全局搜索 `border-l-` 类名。
- **全部删除**；如需强调层级，改用背景色或间距区分，不再使用左侧色条。

---

## P1-2 · Chapter III 字段名泄露

**问题**  
后端原始数据中的字段名（如 `__field_name`、`raw_key` 等）偶尔泄露到前端渲染层，出现在 PDF 中。

**修复方案**
1. 在前端新增 `sanitizeFieldLeaks` 工具函数，路径建议：
   ```
   frontend/src/components/report-print/utils/sanitizeFieldLeaks.ts
   ```
2. 该函数与后端 `_sanitize_field_leaks` 使用**同一套正则规则**，保持前后端清洗逻辑一致。
3. 在 Chapter III 的数据渲染前统一调用 `sanitizeFieldLeaks`，清洗后再传入组件。

---

## 附录：相关文件清单

| 文件 | 说明 |
|------|------|
| `frontend/src/components/report-print/utils/flowColumns.ts` | 已按 Pretext 官方算法重写 `layoutColumn + carveTextLineSlots` |
| `frontend/src/components/report-print/PrintHeader.tsx` | P0-1 调整 `fitHeadline` |
| `frontend/src/components/report-print/PrintChapterI.tsx` | P0-1 移除写死 height/offset |
| `frontend/src/components/report-print/PrintChapterII.tsx` | P0-2 卡片样式、P0-3 pullquote 高度计算 |
| `frontend/src/components/report-print/PrintChapterIII.tsx` | P1-1 删除 border-l、P1-2 调用 sanitize |
| `frontend/src/components/report-print/utils/sanitizeFieldLeaks.ts` | P1-2 新增工具函数 |
