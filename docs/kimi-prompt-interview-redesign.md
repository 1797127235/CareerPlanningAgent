# Kimi 任务：重写 InterviewPage 视觉设计

## 文件位置
`frontend/src/pages/InterviewPage.tsx` — 完整重写视觉和布局，**所有业务逻辑、类型定义、API 调用、状态管理保持不变**。

## 当前问题诊断

1. **Setup 阶段**：居中蓝色渐变圆角大图标 → 标题 → 副标题 → glass 表单卡片。标准 AI slop 布局，跟市面上 80% 的 AI 产品长一样
2. **四个阶段视觉语言不统一**：Setup 是居中表单，Interviewing 是卡片叠加，Results 又是 glass 列表。没有"一个产品"的感觉
3. **Interviewing 阶段**：题目和答案区是两个独立 glass 卡片上下堆叠，割裂感强
4. **Results 阶段**：还行但 glass 卡片堆砌过多，每个 section 都一样的 `glass p-5`

## 设计方向：面试模拟器

这是个**工具**，不是展示页。用户来这里是要做事的——输入岗位、答题、看结果。像 LeetCode 的做题界面，不像一个营销 landing page。

---

## Phase 1: Setup 重设计

### 布局：左右分栏 55:45

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  模拟面试                      ┌─────────────────────┐  │
│                                │ 历史记录             │  │
│  把目标岗位告诉我，             │                     │  │
│  AI 面试官帮你练                │ 后端工程师  78分     │  │
│                                │ 产品经理    62分     │  │
│  ┌──────────────────────┐     │ 前端开发    未完成   │  │
│  │ 目标岗位              │     │                     │  │
│  └──────────────────────┘     └─────────────────────┘  │
│  ┌──────────────────────┐                               │
│  │ JD（可选）            │                               │
│  │                      │                               │
│  └──────────────────────┘                               │
│                                                          │
│  [ 开始模拟面试 ]                                        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 具体要求

**左侧 55%：**
- **删掉**渐变圆角图标
- 标题 `text-[36px] font-bold text-slate-900 tracking-tight` — "模拟面试"，左对齐
- 副标题 `text-[15px] text-slate-400 mt-2 mb-8` — "把目标岗位告诉我，AI 面试官帮你练"
- 表单：不要包在 glass 卡片里，直接裸露在页面上
  - input 和 textarea 用 `bg-white/50 border border-slate-200/60 rounded-xl` 风格
  - label 用 `text-[13px] font-semibold text-slate-600 mb-1.5`
  - 字段之间 `gap-4`
- CTA 按钮：`w-auto`（不要全宽），`px-8 py-3 rounded-xl bg-blue-600 text-white text-[15px] font-bold`
- 按钮下面不需要额外说明文字

**右侧 45%：**
- 标题 `text-[13px] font-bold text-slate-400 uppercase tracking-wider mb-4` — "历史记录"
- 历史列表：每项一行，紧凑排列（不要每项一个 glass 卡片）
  - `py-3 border-b border-slate-100 last:border-0` 简单分隔线
  - 左边：岗位名 `text-[14px] font-semibold text-slate-700` + 日期 `text-[12px] text-slate-400`
  - 右边：分数 `text-[18px] font-black tabular-nums` 或 "未完成" 标签
  - hover 态：`hover:bg-slate-50/50 rounded-lg px-3 -mx-3 transition-colors`
- 无历史记录时：不显示右侧，左侧内容居中占满宽度

**整体：**
- `max-w-[960px]` 容器
- `flex gap-12`，移动端 `flex-col`
- 入场动画：标题先出（delay 0），表单 stagger（delay 0.08），右侧列表（delay 0.15）

---

## Phase 2: Interviewing 重设计

### 布局：沉浸式单列，题目与答案合为一体

```
┌──────────────────────────────────────────────────┐
│  退出                           2 / 5   技术题   │
│  ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░  │
├──────────────────────────────────────────────────┤
│                                                  │
│  你在 Muduo 网络库项目里提到用了 epoll 多路      │
│  复用，请解释一下 epoll 的 ET 和 LT 模式的       │
│  区别，以及你在项目中选择了哪种模式和原因。       │
│                                                  │
│  考察：网络编程 · IO多路复用                      │
│                                                  │
│  ─────────────────────────────────────────────── │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  在这里写下你的回答...                     │   │
│  │                                          │   │
│  │                                          │   │
│  │                                          │   │
│  │                                    156字 │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ← 上一题                            下一题 →   │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 具体改动

1. **题目和答案不再分成两个 glass 卡片**——合成一个连贯区域，中间用一条细线 `border-b border-slate-200/50` 分隔
2. **题目文字放大**：`text-[18px] font-bold text-slate-900 leading-[1.7]`
3. **考察方向**：放题目下方，用 `·` 分隔，`text-[13px] text-slate-400`。去掉 lucide 图标（Target、TrendingUp 太多余了）
4. **进度条全宽**：放在页面顶部贴着导航区，不是卡片内
5. **题号 + 类型标签**：右上角 `text-[13px]`，题号用 `font-bold text-slate-800`，类型用色标签
6. **textarea**：去掉 glass 包裹，直接在分隔线下面。`bg-transparent border-0 focus:ring-0` 无边框风格，像在纸上写字
7. **导航按钮**：左右两端对齐（flex justify-between），最后一题"提交"按钮用 `bg-emerald-600`
8. **最后一题"提交全部答案"按钮**上面加一个小确认：`text-[12px] text-slate-400` — "确认提交后将由 AI 面试官评估"

---

## Phase 3: Evaluating 重设计

和简历定制一样，用**进度叙事**替代大 spinner：

```
正在评估...

✓ 技术题回答分析           已完成
✓ 行为题 STAR 结构检查     已完成  
● 综合评分与建议生成       进行中...

通常 15-30 秒
```

- 用 `useState` + `useEffect` 定时器做假进度（3s 后第一步完成，6s 后第二步，之后第三步转圈）
- 每步一行，`flex items-center gap-3`
  - 完成：`CheckCircle2 text-emerald-500` + `text-slate-600`
  - 进行中：`Loader2 animate-spin text-blue-500` + `text-slate-800 font-semibold`
  - 等待中：`Circle text-slate-200` + `text-slate-400`
- 不要大渐变图标

---

## Phase 4: Results 重设计

### 顶部得分区

不要 glass 卡片。直接一个大号得分 + 评语：

```
78                              总体表现不错，技术基础扎实，
综合得分                        行为题回答结构可以更清晰。
████████████████████████████░░
```

- 得分 `text-[64px] font-black tabular-nums` + `scoreColor`
- "综合得分" `text-[12px] text-slate-400 mt-1`
- 评语在右侧 `text-[14px] text-slate-600 leading-relaxed max-w-[400px]`
- 进度条在得分正下方，`h-1.5`（不是 h-3 那么粗）

### 逐题评分

去掉每题一个 glass 卡片。用紧凑列表：

```
01  技术题 · 网络编程                                    82
    你在 Muduo 网络库项目里...

    ✓ 对 epoll ET/LT 区别解释清晰
    △ 可以补充为什么选择 LT 模式的性能考量
    
    ▸ 参考回答

────────────────────────────────────────────────────────

02  行为题 · 团队协作                                    65
    ...
```

具体：
- 编号 `text-[12px] font-bold text-blue-600/30 tabular-nums`
- 类型 + 方向 `text-[12px] text-slate-400`
- 题目摘要 `text-[13px] text-slate-500 mt-1 line-clamp-1`（只显示一行，不是完整题目）
- 得分在行尾 `text-[22px] font-black tabular-nums`
- strengths 用 `✓` 前缀 `text-emerald-600`，improvements 用 `△` 前缀 `text-amber-600`
- 各题之间用 `border-b border-dashed border-slate-200/60 py-5`
- 不要用 lucide Star 图标做 strengths 前缀（太花哨）

### 技能缺口 + 改进建议

合并为一个区域（不要两个 glass 卡片）：

```
需要关注                          改进建议

Redis · 分布式系统                1. 技术题多用具体数字...
                                  2. 行为题按 STAR 结构...
                                  3. 场景题先确认需求边界...
```

- 左右分栏或上下排列都行
- 技能缺口用 inline 标签 `px-2.5 py-1 rounded-lg bg-amber-50 text-amber-700 text-[13px]`
- 改进建议用编号列表，`text-[13px] text-slate-600 leading-relaxed`

### 底部操作

"再来一次" 按钮不居中，放左下角和"返回首页"并排：

```
[ 再来一次 ]    返回首页
```

---

## 技术约束

- framer-motion（已安装），ease `[0.23, 1, 0.32, 1]`
- lucide-react 图标（已安装）
- rawFetch from '@/api/client'
- @tanstack/react-query
- Tailwind v4，glass 类可用
- **所有业务逻辑保持不变**：状态机 4 阶段、API 调用、handleNext/handlePrev/handleSubmit/handleRestart/handleLoadHistory 全部原封不动
- 不引入新依赖

## 禁止

- 不要居中大图标 + 标题 + 副标题的 AI slop 布局
- 不要 gradient 背景的圆角图标
- 不要每个 section 都套 glass 卡片（结果页尤其要克制）
- 不要 gradient text
- 不要 bounce/elastic 动画
- 不要在 Interviewing 阶段把题目和答案分成两个独立卡片
