# Design System v2 — Anthropic + 中文衬线

## Color
- `bg`: #f0ebe3（奶油色背景）
- `bg-card`: #e8e2d8（卡片背景，同色系稍深）
- `bg-hover`: #e2dbd0（卡片 hover）
- `text-primary`: #1a1a1a（标题、正文主色）
- `text-secondary`: #5c5c5c（描述文字）
- `text-tertiary`: #8a8a8a（caption、辅助信息）
- `border`: #d5cfc5（分隔线、边框）
- `accent`: #c45c3e（珊瑚橙，来自第三种设计，仅用于极少量强调）
- `dark-section`: #1a1a1a（深色区域背景，如 Anthropic Project Glasswing 区块）

## Typography
- 中文标题：`Noto Serif SC`, serif（呼应第三种设计的杂志感）
- 中文正文：`Noto Sans SC`, sans-serif（保证可读性）
- 英文：`Commissioner`, sans-serif（保留现有）
- H1: 56px / weight 600 / line-height 1.15 / letter-spacing -0.02em
- H2: 32px / weight 600 / line-height 1.25
- Body: 15px / weight 400 / line-height 1.7
- Caption: 12px / uppercase / letter-spacing 0.08em / text-tertiary

## Spacing
- Section: 80px vertical
- Container: max-width 1200px, padding 48px horizontal
- Card: padding 32px, gap 24px
- List item: padding 18px vertical, 1px border-bottom

## Border Radius
- Cards: 16px
- Buttons / Tags: 100px (pill)

## Shadow
- 不用。靠颜色层级和留白区分。

## Motion
- Entrance: fade-up 0.5s, cubic-bezier(0.23, 1, 0.32, 1)
- Hover: opacity 0.7 或 subtle 背景色变化（0.2s ease）

## Component Notes
- 按钮：黑色 pill（bg #1a1a1a, text white），ghost 版本（透明底 + border）
- 标签：黑色 solid pill（如"杠杆区"），ghost pill（如"起步岗位"）
- 列表项：细线分隔 + hover opacity 变化
- 元数据行：大写 caption 标签 + 细线分隔（DATE / CATEGORY 风格）
