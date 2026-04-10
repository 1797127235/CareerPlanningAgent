---
name: feedback_design_style
description: 前端设计风格确定——Dimensional Layering（多层深度叠加），紫色系，DM Sans 字体
type: feedback
---

前端设计方案最终确定（2026-03-31），基于 demo-f.html，所有页面统一此风格。

**Why:** 用户经历 10+ 轮迭代（青色赛博朋克→金橙→紫粉→冰蓝→钴蓝→极简→多种 demo 对比），最终选定 Demo F: Dimensional Layering。

**How to apply:**

## 风格: Dimensional Layering（多层深度叠加）
- 参考文件: frontend/public/demo-f.html
- 核心概念: 主内容在前景清晰锐利，背后有模糊的、带角度旋转的装饰面板，营造空间纵深
- 每层不同 opacity + blur + rotation
- 鼠标移动时背景层有视差偏移

## 颜色
- 背景: #0C0C0E 深灰黑
- 强调色: #8B5CF6 紫色系
- 卡片背景: 毛玻璃 backdrop-filter:blur(40px) + rgba 半透明
- 文字: 白色系，次级用 rgba(255,255,255,0.5-0.7)

## 字体
- 主字体: DM Sans + Noto Sans SC
- 非 Inter/Roboto/Arial

## 关键效果
- 4 级阴影系统 (sm/md/lg/xl)
- 背景装饰面板: 假 UI 元素（图表/卡片/数据），35-55% opacity, 2-6px blur, 2-5deg rotation
- 紫色渐变按钮
- 噪点纹理叠加
- 入场动画 fade + translateY

## 禁忌
- 不要粒子系统（用户嫌弃过）
- 不要花哨的鼠标交互
- 不要 emoji 做图标
- 不要底部 footer/信任徽章
- 不要 Inter/Roboto 等泛用字体
