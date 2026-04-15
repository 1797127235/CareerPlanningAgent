# v2 ReportPage · 给 22 岁迷茫学生的编辑部来信

> 创建：2026-04-15
> 状态：待 Kimi 实施
> 依赖：
> - `.impeccable.md` v2.0（已落地）
> - `docs/v2-frontend-scaffold-spec.md`（必须先完成脚手架）
> - 复用 backend `/report/generate` endpoint，不动后端

---

## I. 用户 Job to be done

**用户**：上传简历生成报告的中国 CS/IT 大三/大四学生。

**场景**：
- **生成后认真读一次**（10-20 分钟的长 form 阅读，不是扫一眼）
- **之后偶尔回看复习**（考虑方向时 / 面试前 / 迷茫时重读）
- **读完想要两件事**：
  1. "我懂了我是谁"（自我画像被说中 → 心里落地）
  2. "我知道下一步动什么"（具体 actionable → 不空虚）

**不该让用户感到**：
- ❌ 像在看体检报告（一堆"指标"）
- ❌ 像在看 dashboard（仪表盘 + metric card）
- ❌ 像在被测评（70 分之类审判数字）
- ❌ 像被 AI 生成的泛泛而谈（"你有创造力、逻辑强、沟通好" — 谁都适用）

**该让用户感到**：
- ✅ 像收到一封专门为他写的长信（来自懂他的学长）
- ✅ 某一段被戳中（"说的就是我"）
- ✅ 读完合上，有"知道下一步做什么"的踏实感

---

## II. 顶层设计 · 报告是一封信，不是一个页面

**Editorial 强度 🌟🌟🌟 最强**（按 `.impeccable.md` v2.0 分级）

- Hero 用 `--fs-display-xl`（clamp 42-96px）
- 段落宽 65ch，line-height 1.85（中文）
- 章节之间纵向呼吸 160px+
- **每章必用**：Kicker + ChapterOpener + DropCap 首段
- **关键章必用**：PullQuote（引用用户简历原话 or AI 洞察金句）
- Page padding：桌面 128px（比 GrowthLog 的 64px 更阔）

**不用的元素**：
- ❌ 进度条 / 覆盖率 / 分数圆圈（审判数字全砍）
- ❌ metric card 矩阵（dashboard 感）
- ❌ 横排 chip 堆叠（数据 dump 感）
- ❌ Tab 切换（长 form 一路读下去，不分 tab）

---

## III. IA · 4 章结构（像学长写给你的长信）

### Prologue · 为你而写

（小段开场，不是章节）

- Kicker: `EDITORIAL · 编辑部来信`
- body: 一段短开场 `"这份报告是基于你的 {资历摘要} 写的。不是模板 — 每一段都在回答一个具体问题："`
- body: "你是谁？你能去哪？你们之间差什么？下一步怎么动？"
- 装饰: 顶部 `<SectionDivider numeral="·" />`

---

### Chapter I · 你是谁

**Kicker**: `CHAPTER I · WHO YOU ARE`

**ChapterOpener**: 装饰罗马数字 `I` + 大字 hero

**Hero title**: 来自 AI 合成的一句人物画像
> 例："你像一个 **被工程问题吸引的人** — 喜欢把混乱变成秩序。"

（数据源：`profile.summary` 或 `report.persona_headline` — 待 Kimi 查后端）

**Body（3-5 段）**：
- **第 1 段** 必用 `<DropCap>`：从简历抽取的核心特质总结（不是 "你有 A / B / C 三个优点"，是一段连贯叙述）
- **第 2-3 段**：具体例子 / 项目 / 经历佐证（要引用用户简历原文）
- **第 4-5 段**：性格偏好与工作方式（SJT / 测评数据如果有）

**PullQuote**（用户简历原话）：
> "{用户简历中的某个 impact 句}"  
> — 来自你填写的「{项目名}」

**验收**：读完这一章，用户应该觉得"说的就是我，不是泛泛"。如果 AI 出的是 "你有创造力、逻辑强、沟通好" 这种通用话，**重生成**。

---

### Chapter II · 你能去哪

**Kicker**: `CHAPTER II · WHERE YOU CAN GO`

**ChapterOpener**: 装饰罗马数字 `II`

**Hero title**: 推荐方向 + 为什么和你契合
> 例："**系统 C++ 工程师** 这条路，和你契合的是 **把复杂拆成简单** 的那部分。"

**Body**：
- **第 1 段** 必用 `<DropCap>`：为什么这个方向
- **第 2 段**：这个方向的日常做什么 — 具体场景描述（不是职责清单）
- **第 3 段**：为什么不推荐你去的方向（1-2 个反推荐，诚实说）
- **第 4 段**：可选替代方向（1-2 个次选，说清差异）

**数据源**：`report.recommended_roles[]`（待 Kimi 查后端）

**交互**：主推荐方向有一个 `<button>` "去图谱看这个路径 →" 跳 `/graph?target=xxx`

**不做**：路径节点横排 chip / 5 个圆圈那种展示（留图谱页去做）

---

### Chapter III · 你们之间差了什么

**Kicker**: `CHAPTER III · THE GAP`

**ChapterOpener**: 装饰罗马数字 `III`

**Hero title**: 诚实但不审判
> 例："你已经接近了 — 还差 **两件事** 的距离。"

**Body**：
- **第 1 段** 必用 `<DropCap>`：你已经掌握的（**先肯定**，按 Brand Principle 2 共情前置）
- **第 2 段**：真正的差距是什么（2-3 件具体的事，不是 "Python / SQL / 算法" 这种技能清单）
- **第 3 段**：每个差距有多远（不给百分比，用"一个项目能补上" / "一学期刻意练习" 这种软化描述）

**PullQuote**（关键金句）：
> "差距不是你不够 — 是你还没给自己机会碰到这些事。"

**不做**：
- ❌ 覆盖率 bar（R4 烦的那个被砍了）
- ❌ 核心/重要/加分三层 chip（数据 dump）
- ❌ "70 分" 分数

**数据源**：`report.gap_analysis`（待 Kimi 查后端，可能需要映射）

---

### Chapter IV · 下一步从哪动

**Kicker**: `CHAPTER IV · WHAT TO DO NEXT`

**ChapterOpener**: 装饰罗马数字 `IV`

**Hero title**: 降门槛的第一步
> 例："先从 **这一件** 开始。"

**Body（3 个 actionable，每个一小节）**：

每个小节结构：
```
<h3>一 · 这周做 {动作}</h3>
<p>为什么这件事先做 — 一段理由</p>
<p>具体动作（不是"学习 Python"，是"用 Python 写一个 {X} 的小脚本"）</p>
<button>记到成长档案 →</button>  // 跳 /growth-log 并预填内容
```

**数据源**：`report.action_plan`（backend/services/report/action_plan.py 输出）

**CTA 按钮交互**：点击后跳 `/growth-log` 并打开「记一笔」弹窗，预填动作描述。

**验收**：用户读完合上，脑子里应该能复述"我这周要做的第一件事是什么"。

---

### Epilogue · 这不是终点

（小段收尾，不是章节）

- body: 一段温暖收尾 `"这份报告不是一个诊断。是一个起点。你会变，它也会。"`
- body: `"每记一笔，这封信就会被重写一次 — 等你下次回来看。"`
- 底部细节：生成时间戳 + 用 mono 字体 `"generated at 2026-04-15"`

---

## IV. 数据契约

**后端不动** — 完全复用 `POST /report/generate` 现有 endpoint。

**但数据可能需要映射**：

| v2 章节需要 | 当前 backend 是否有 | 如果缺 |
|---|---|---|
| Chapter I persona_headline | 查 `backend/services/report/narrative.py` 看有没有"一句画像" | 如果没有：新增 headline 字段或从 `summary` 取首句 |
| Chapter II recommended_roles | 应该有（现有 ReportPage 就在用） | 直接用 |
| Chapter III gap_analysis | 查 `skill_gap.py` 输出 | 可能需要重组表达（去审判化） |
| Chapter IV action_plan | 应该有（`action_plan.py`） | 直接用 |
| PullQuote 来源 | 从 profile 原始 text / project description 抽 | LLM 生成金句（可以 on-the-fly） |

**Kimi 第一步**：读 `backend/services/report/pipeline.py` + `narrative.py` + `action_plan.py`，列出 **当前 endpoint 返回什么字段**。如果字段不够支持 4 章 IA，**标出差距但不立即改后端** — 先用现有字段能做到哪步做哪步，缺的字段用合理 fallback（如 "No persona yet" 之类），后续 P4.5 再补后端。

---

## V. 组件拆分

```
src/pages/ReportPage.tsx              # 顶层容器，调用 report API，错误/加载态
src/components/report-v2/             # 新子目录
├── ReportPrologue.tsx                # 开场小段
├── ReportChapterI.tsx                # 你是谁
├── ReportChapterII.tsx               # 你能去哪
├── ReportChapterIII.tsx              # 差距
├── ReportChapterIV.tsx               # 行动
└── ReportEpilogue.tsx                # 收尾
```

每个 ChapterX 内部结构：

```tsx
import { Chapter, ChapterOpener, DropCap, PullQuote, Kicker } from '@/components/editorial'

export function ReportChapterI({ data }: { data: PersonaData }) {
  return (
    <>
      <ChapterOpener numeral="I" title={<>{data.headline}</>} />
      <Chapter numeral="I" label="你是谁" title={...}>
        <DropCap>{data.paragraphs[0]}</DropCap>
        <p>{data.paragraphs[1]}</p>
        <p>{data.paragraphs[2]}</p>
        <PullQuote attribution={`来自你填写的「${data.quote_source}」`}>
          {data.quote_text}
        </PullQuote>
        <p>{data.paragraphs[3]}</p>
      </Chapter>
    </>
  )
}
```

---

## VI. 布局与响应式

**桌面**（≥1024px）：
- 内容最大宽度 `max-w-[900px] mx-auto`
- 左右 padding `px-32`（128px）
- 章节之间 `py-32`（128px）

**平板**（768-1024px）：
- 内容最大宽度 `max-w-[720px]`
- 左右 padding `px-16`
- 章节之间 `py-24`

**移动**（<768px）：
- 左右 padding `px-6`（24px）
- 章节之间 `py-16`
- DropCap 字号自适应缩到 48px
- PullQuote `--fs-quote` 自动 clamp 缩到 20px

---

## VII. Motion（scroll-triggered）

- **ChapterOpener** 装饰罗马数字：用 `useScroll` + `useTransform`，滚入视野时 opacity 0.3→0.6 + scale 0.95→1
- **Chapter** body：章节进入视野时 staggered fade-in（每段 80ms 间隔）
- **PullQuote**：进入视野时 opacity 0→1 + 上下线条宽度 0→100%（400ms ease-out）
- **DropCap**：首字进入视野时有一个 subtle color 从 ink-2 → chestnut 的过渡（600ms）

**全部受 `prefers-reduced-motion: reduce` 控制**，关闭时立即显示。

---

## VIII. 验收标准

1. **读起来像一封信**：owner 合上浏览器后能一句话说出"我是谁" + "下周做什么"
2. **无审判数字**：整页无百分比 / 分数 / 进度条 / 评级
3. **editorial 装饰齐**：每章都有 Kicker + ChapterOpener + DropCap 首段；Chapter I/III 必有 PullQuote
4. **长度合适**：总阅读时长 10-15 分钟（不要太短像总结，不要太长像 wiki）
5. **数据不是模板**：对比两个不同简历生成的报告，persona_headline / PullQuote 必须不同（如果同就是模板化）
6. **tsc 0 错误 + build 通过**
7. **移动端可读**：iPhone 14 视角下每段 ≤ 40 字/行，hero 字号不超出视野

---

## IX. 不做的事

- ❌ 不动 backend（API 完全复用 + 映射）
- ❌ 不做 PDF 导出（后续）
- ❌ 不做报告版本比较（"本次 vs 上次"，后续）
- ❌ 不做分享功能（后续）
- ❌ 不做 Tab / 折叠 / 侧边导航（长 form 一路读下去）
- ❌ 不做 dashboard 风格的 hero metric

---

## X. 给 Kimi 的执行顺序

**前置**：`docs/v2-frontend-scaffold-spec.md` 必须已完成（`frontend-v2/` 骨架 + 7 个 editorial 组件）

1. **读后端** — 读 `backend/services/report/{pipeline,narrative,action_plan,skill_gap}.py`，列出 `POST /report/generate` 实际返回的 field shape
2. **写类型** — `frontend-v2/src/api/report.ts` 扩展/新增 `ReportV2Data` 类型，对齐后端 shape + 4 章 IA 的字段映射
3. **缺字段处理** — 如果后端 headline / quote / gap_soft_language 等字段缺，**用 fallback**（例："暂无个性化画像，请补充简历"），不改后端
4. **实现 6 个 chapter 组件** — `src/components/report-v2/` 下 6 个组件（Prologue + I-IV + Epilogue）
5. **实现 ReportPage.tsx** — 顶层 + loading / error / empty 状态
6. **路由注册** — `src/App.tsx` `/report` → ReportPage
7. **Motion 集成** — framer-motion 按 §VII 描述
8. **验收** — §VIII 7 项逐项对
9. **截图** — 每章单独一张 + 整页一张，发 owner

**完成后回消息**：`"ReportPage v2 完成 + 7 张截图"`

---

**完成判定**：owner 打开 `http://localhost:5174/report` 读完整页，**感到收到一封信** — 而不是看了一个 dashboard。
