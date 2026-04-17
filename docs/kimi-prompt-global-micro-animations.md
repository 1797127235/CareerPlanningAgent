# Kimi 任务：全局微动效补充

## 设计调性

品牌是"柔软 · 可靠 · 像一本自己的档案本"。动效要**安静精致**——不是 confetti 和 bounce，而是每个交互都有重量和回应。像翻一本做工精良的笔记本，每个动作都有恰到好处的阻尼感。

**统一参数：**
- ease: `[0.22, 1, 0.36, 1]`（expo-out）
- 入场 fade: 150-300ms
- hover 反馈: 200ms
- 按压反馈: `active:scale-[0.98]`
- 不用 bounce / elastic / spring

---

## 1. GrowthLogV2Page（成长档案 — 当前几乎无动效）

文件：`frontend/src/pages/GrowthLogV2Page.tsx`

### 1.1 添加 framer-motion import

在文件顶部加：
```tsx
import { motion, AnimatePresence } from 'framer-motion'
```

### 1.2 页面入场

找到页面最外层容器（`return` 后的第一个 `<div>`），包一层 motion：

```tsx
<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ duration: 0.2 }}
>
  {/* 原有内容 */}
</motion.div>
```

### 1.3 筛选标签切换

找到 FILTERS 渲染的地方（`全部 / #项目 / #面试 / #学习 / 计划` 标签），给每个标签加 hover 和 active 反馈：

在标签的 className 中加：
```
hover:bg-slate-50 active:scale-[0.97] transition-all duration-200
```

选中态标签加微缩放：
```
scale-[1.02]
```

### 1.4 时间线条目 stagger 入场

找到渲染日期分组和条目列表的地方。给每个日期分组的标题加 fade：

```tsx
<motion.h3
  initial={{ opacity: 0, x: -8 }}
  animate={{ opacity: 1, x: 0 }}
  transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
>
  {group.label}
</motion.h3>
```

给每个条目加 stagger 入场（如果条目是用 `.map()` 渲染的）：

```tsx
<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ delay: index * 0.03, duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
>
  {/* 原有的 EntryCard / PlanRow / LegacyRecordRow */}
</motion.div>
```

注意：`delay: index * 0.03` 间隔很短（30ms），不会让用户感觉在等，只是有一个"逐条浮现"的微妙节奏感。

### 1.5 条目卡片 hover

找到 EntryCard / LegacyRecordRow 的外层容器，加 hover 反馈：

如果是在 `GrowthLogV2Page.tsx` 中直接渲染的包裹 div，加：
```
hover:bg-white/50 hover:-translate-y-px transition-all duration-200
```

如果需要进入组件文件改，只改 className 不改逻辑。

### 1.6 QuickInput 提交反馈

找到 QuickInput 组件的发送按钮，加：
```
hover:-translate-y-0.5 hover:shadow-sm active:translate-y-0 active:scale-[0.97] transition-all duration-200
```

---

## 2. ExplorePage（岗位探索 — 当前几乎无动效）

文件：`frontend/src/pages/ExplorePage.tsx`

### 2.1 添加 framer-motion import

```tsx
import { motion } from 'framer-motion'
```

### 2.2 页面入场

最外层容器包 motion：
```tsx
<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ duration: 0.2 }}
>
```

### 2.3 岗位选择器 hover

找到 JobPickerButton 的使用处或组件内部，给选择器按钮加：
```
hover:border-blue-300 hover:bg-blue-50/30 hover:-translate-y-px transition-all duration-200
```

### 2.4 对比行 stagger 入场

如果页面有一个列表展示对比维度（如 ComparisonRow），给每行加：
```tsx
<motion.div
  initial={{ opacity: 0, y: 6 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ delay: index * 0.04, duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
>
  <ComparisonRow ... />
</motion.div>
```

### 2.5 "设为目标" 按钮

找到 chooseAsTarget 相关的按钮，加满 hover 反馈：
```
hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:scale-[0.98] transition-all duration-200
```

---

## 3. HomePage（首页 — 有一些动效，补充 hover）

文件：`frontend/src/pages/HomePage.tsx`

### 3.1 导航卡片 hover 加强

找到首页的功能入口卡片/按钮（如"我的画像"、"岗位图谱"、"成长档案"等导航块），统一加：
```
hover:-translate-y-0.5 hover:shadow-sm transition-all duration-200
```

### 3.2 热力图区域

如果 ActivityHeatmap 组件的每个格子没有 hover 效果，给格子加：
```
hover:ring-2 hover:ring-blue-300/50 hover:scale-110 transition-all duration-150
```

（注意：这个可能需要改 ActivityHeatmap 组件，如果组件是独立文件就进去改）

### 3.3 统计数字

如果首页有统计数字（如"诊断 N 次"、"面试 N 次"），这些数字不需要计数动画（符合反量化原则），但容器可以加入场 fade：
```tsx
<motion.div
  initial={{ opacity: 0, y: 4 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ delay: 0.1, duration: 0.25 }}
>
```

---

## 4. ProfilePage（画像页 — 有一些动效，补充 hover）

文件：`frontend/src/pages/ProfilePage.tsx`

### 4.1 技能标签 hover

找到技能列表的 tag/badge 渲染，给每个技能标签加：
```
hover:scale-[1.05] hover:shadow-sm transition-all duration-150
```

### 4.2 Section 卡片 hover

画像页通常有多个 section（教育、技能、项目等），给每个 section 的容器加：
```
hover:border-slate-300/60 transition-colors duration-200
```

不加 translate 或 shadow（画像页是阅读页，不需要卡片飞来飞去）。

---

## 5. 全局通用：按钮 hover 标准

在整个项目中，所有主要操作按钮（bg-blue-600 / bg-emerald-600 等实心按钮）应该统一有：

```
hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:shadow-none active:scale-[0.98] transition-all duration-200
```

所有次要按钮 / ghost 按钮应该有：
```
hover:bg-slate-50 active:scale-[0.97] transition-all duration-150
```

**搜索范围**：在以上 4 个文件中找到所有 `<button` 元素，检查是否已有 hover 动效，没有的补上。

---

## 技术约束

- framer-motion（已安装）
- ease: `[0.22, 1, 0.36, 1]` 或 Tailwind 的 `ease-out`
- 只用 `transform` 和 `opacity`（GPU 加速）
- `prefers-reduced-motion` 时 framer-motion 自动处理
- 不引入新依赖

## 禁止

- 不要 bounce / elastic / spring 缓动
- 不要 confetti / 粒子效果
- 不要 gradient text 动画
- 不要给大量列表项（>20）加 stagger（性能问题）— 超过 20 项时去掉 delay
- 不要改任何业务逻辑
- 不要改布局结构，只加 className 和 motion 包裹
