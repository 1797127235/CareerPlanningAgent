# v2 ProfilePage · 你讲给系统听的档案

> 创建：2026-04-15
> 状态：待 Kimi 实施
> 依赖：
> - `.impeccable.md` v2.0（已落地）
> - `docs/v2-frontend-scaffold-spec.md` 脚手架（已完成 `7d660b1`）
> - `docs/v2-report-page-spec.md` ReportPage（已完成 `8604e16`+`1607175`）
> - 复用 backend `/profiles` endpoints，不动后端

---

## I. 用户 Job to be done

**用户**：中国 CS/IT 大三/大四学生（已登录 app）。

**三种场景**：

1. **首访** — 还没有 profile（刚注册完 / 刚登录）
   - 要做的：上传简历 / 手动录入 → 系统生成初始 profile
   - 情绪：不知道系统能干啥，怕填错、怕被评判

2. **复访** — 已有 profile（之前上传过）
   - 要做的：看档案状态 / 补细节 / 编辑字段 / 换目标 / 点开 SJT
   - 情绪："我之前讲给它听过了，它还记得吗"

3. **整理** — 写完 Growth Log 后回来更新 profile
   - 要做的：把新的项目 / 技能 / 实习加进来
   - 情绪：把走过的路留档

**读完这一页，用户应该感到**：
- ✅ "它在认真听我讲" — 被看见，不是被评测
- ✅ "我还可以再讲一些" — 补充门槛低，不是强制
- ✅ "我掌握编辑权" — 什么都能改

**不该让用户感到**：
- ❌ 被打分（`overall_score 70 分 / 行业平均 65 分`）
- ❌ 被分类（`zone: danger` / `AI风险` 标签）
- ❌ 信息密度压迫（一屏塞满 card 矩阵）
- ❌ 表单感（Bootstrap form / 必填红星）

---

## II. 顶层设计 · Profile 是"你对系统的自述"

**Editorial 强度 🌟🌟🌟 强**（按 `.impeccable.md` v2.0 分级）

- Hero（Prologue）用 `--fs-display-xl`（clamp 42-96px）
- 段落宽 `65-72ch`，line-height 1.85（中文）
- 章节之间纵向呼吸 112-128px
- **每章必用**：Kicker + ChapterOpener
- **关键章必用**：DropCap 首段 + PullQuote（用户简历原话）
- Page padding：桌面 `px-20`（比 Report 的 `px-32` 略紧，因为 Profile 有更多交互元素需要点）
- 双列布局：`lg:grid-cols-[1fr_200px]` 右侧 sticky TableOfContents

**不用的元素**

- ❌ `quality.overall_score` / `industry_avg` / `completeness` / `competitiveness` 任何百分比审判
- ❌ `zone` 红绿灯色 / `replacement_pressure` AI 风险标签
- ❌ `glass` 毛玻璃 / `cyan/blue-600` 蓝紫色
- ❌ 横排 chip 矩阵（Skills/Knowledge 保留 chip 但按编辑体重做）

---

## III. IA · Prologue + 4 章 + Epilogue

### Prologue · 欢迎 / 状态概览 + 上传入口

（hero 区，页面最顶）

**Kicker**: `OPEN FILE · 你的档案`

**Hero title**（按 profile 是否存在分支）：

- 没 profile（首访）：
  > **还没开始讲给我听。<br/>一份简历，或者几句话，都行。**
- 已有 profile：
  > **我们已经认识 {days_since_first_profile} 天了。<br/>最近讲的是 {last_updated_section}。**

**Body（1-2 段）**：
- 首访：一段温柔开场说"这份档案只给系统看，不会给任何第三方"
- 已有：一段"下面是你之前讲的，随时可以补"

**Action Bar**（hero 下方 2 个 CTA）：

```
[主 CTA] 上传一份简历
[次 CTA] 手动讲给我听（ManualProfileForm）
```

首访时主 CTA 大 + ember 色，已有时主 CTA 小且文案变"重新上传"/"补一笔"。

---

### Chapter I · 你从哪里来

**Kicker**: `CHAPTER I · WHERE YOU COME FROM`

**ChapterOpener**: 装饰大罗马数字 `I`

**Hero title**:
- 有数据：`你在 {school}，学 {major}，已经走过 {internship_count} 段实习 + {project_count} 个项目。`
- 空：`先讲讲你从哪里来 —— 学校、专业、做过的事。`

**Body（章节分 3 小节）**：

#### 1.1 · 你在读什么
- DropCap 首段：用 narrative 描述学历（"你在 XXX 学 XXX，{experience_years} 年经验"）
- 小 action 按钮：`补充教育背景 →`（点开内联编辑）

#### 1.2 · 你实习过哪些地方
- 每个 internship 一个 card（基于 `PaperCard`）：
  - `{company}` — `{role}`，`{duration}`
  - 简短 highlights（保留用户原话）
  - tech_stack chip（小 chip，不是横排堆叠）
- CTA：`再加一段实习 →`
- 空状态：`还没有实习记录 —— 如果有，加一段；没有也没关系。`

#### 1.3 · 你做过哪些项目
- 每个 project 一个 card：
  - 项目名 + 技术栈
  - 用户填写的描述
  - 如果有 PullQuote 级别的好句子（`description.length > 30`），用 `<PullQuote>` 突出
- CTA：`再加一个项目 →`

---

### Chapter II · 你会什么

**Kicker**: `CHAPTER II · WHAT YOU KNOW`

**Hero title**:
- 有数据：`你提到了 {skills.length} 个技能，{knowledge_areas.length} 个知识领域。`
- 空：`技能和知识，加一个是一个 —— 以后 Growth Log 会帮你记住新学到的。`

**Body**:

#### 2.1 · 技能清单
- Skill chip，按 `level` 分 4 组（expert / proficient / familiar / beginner）
- 每组一行横排 chip，chip 色按 level：
  - expert → `chestnut` 深栗
  - proficient → `moss` 苔绿
  - familiar → `ink-2` 中灰
  - beginner → `ink-3` 浅灰
- 每组小标题：`熟练掌握（{count}）/ 能用（{count}）/ 了解（{count}）/ 刚接触（{count}）`
- chip 可点击进入编辑状态（inline edit level 或删除）
- CTA：`加一个技能 →`（展开输入框）

#### 2.2 · 知识领域
- Knowledge areas 以 chip 展示，淡色（`bg-[var(--bg-paper)] text-[var(--ink-2)]`）
- CTA：`加一个领域 →`

---

### Chapter III · 你是怎样的人

**Kicker**: `CHAPTER III · HOW YOU WORK`

**Hero title**:
- 有 SJT 数据：`你做事的方式里，最突出的是 {top_soft_skill_name}。`
- 没有：`想知道你在团队里怎么做事吗？{3-5 分钟}小测。`

**Body**:

#### 3.1 · 软技能画像（SoftSkills）

- 4-6 个维度，每个维度一行：
  - 维度名 + 一句叙事化描述（**不要 score 数字**）
  - 例："**沟通表达** · 你在团队讨论里是那种先听再说的人，话不多但准。"
  - 小 tag：level 文字化（"高 / 中 / 低"变成"**明显** / **清楚** / **在路上**"）
- 如果有 `evidence` 字段，展示为 PullQuote

#### 3.2 · 情境判断（SJT）
- 如果没做过：大 CTA card
  > **一个 3 分钟的情境小测 — 帮系统理解你做事的偏好。**
  > [开始测试 →]
- 如果做过：展示 SjtResult（待后端 shape 确定）

---

### Chapter IV · 你想去哪

**Kicker**: `CHAPTER IV · WHERE YOU WANT TO GO`

**Hero title**:
- 有 goal：`你现在瞄的是 {target_label}。`
- 没 goal：`先不急着定方向 —— 先看看有什么选项。`

**Body**:

#### 4.1 · 你的目标
- 当前 CareerGoal（如果有）：
  - `{target_label}` · 从 `{from_node_label}` 过去
  - 不显示 `safety_gain / salary_p50 / total_hours`（这些是仪表盘数据，Graph 页展示）
  - CTA：`去图谱看路径 →` 跳 `/graph?target=xxx`
  - 次级 CTA：`换个方向 →`
- 空状态：一句话引导 + "让 AI 帮我推荐" / "我去图谱探索" 双 CTA

#### 4.2 · 还可能去的方向（Recommendations）
- 每个 recommendation 一张 `PaperCard`：
  - `{label}` —— 简短一句 `{reason}` 作为副标
  - **不显示** `affinity_pct` / `zone` / `replacement_pressure`
  - CTA：`看看这个方向 →`
- 最多显示 3 个，"展开更多"可以看全部

---

### Epilogue · 下一件事 / 档案历史

（简短收尾）

- 如果 profile 不完整（缺名字 / 缺实习 / 缺软技能）：
  > `还有几件事可以讲 — 但不用现在做完。`
  > chip list 可点击跳对应章节编辑
- 底部细节：`上次更新 {updated_at}`，用 mono 字体
- 底部一句温柔话：`这份档案只给你自己和懂你的系统看。`

---

## IV. 数据契约

**后端不动** — 完全复用 `GET /profiles/me`（或现有 profile 获取 endpoint）。

**字段映射**（基于 `frontend/src/types/profile.ts` 的 `ProfileData`）：

| Chapter | 消费字段 |
|---|---|
| Prologue | `name / updated_at / created_at` |
| Chapter I | `profile.education / profile.experience_years / profile.internships / profile.projects` |
| Chapter II | `profile.skills / profile.knowledge_areas` |
| Chapter III | `profile.soft_skills` + SJT 结果（需查 backend） |
| Chapter IV | `career_goals / graph_position` + 独立 `/recommendations` endpoint |
| Epilogue | `name` 是否缺 + `updated_at` + 章节完成度（前端自算） |

**显式砍掉的字段**（不消费）：

- `quality.overall_score` / `industry_avg` / `completeness` / `competitiveness` / `confidence`
- `quality.dimensions` 的 score 数字（dimensions 本身保留但只用 label）
- `graph_position.safety_gain` / `salary_p50` / `total_hours`
- `Recommendation.affinity_pct` / `zone` / `replacement_pressure`

**章节完成度算法**（替代 quality.completeness）：

```ts
const sectionsCompleted = [
  !!profile.name,
  !!profile.education?.school,
  (profile.internships?.length ?? 0) > 0 || (profile.projects?.length ?? 0) > 0,
  (profile.skills?.length ?? 0) > 0,
  Object.keys(profile.soft_skills ?? {}).length > 0,
  (career_goals?.length ?? 0) > 0,
].filter(Boolean).length
// 用于 Epilogue "还有 N 件事可以讲"，不给百分比
```

---

## V. 组件拆分

```
src/pages/ProfilePage.tsx                    # 顶层：load profile + loading/error/empty
src/components/profile-v2/
├── ProfilePrologue.tsx                      # 上传 + 状态概览 hero
├── ProfileChapterI.tsx                      # 从哪里来（Edu + Internships + Projects）
├── ProfileChapterII.tsx                     # 会什么（Skills + Knowledge）
├── ProfileChapterIII.tsx                    # 怎样的人（SoftSkills + SJT）
├── ProfileChapterIV.tsx                     # 想去哪（Goal + Recommendations）
├── ProfileEpilogue.tsx                      # 补完引导 + 更新时间
├── cards/
│   ├── EducationCard.tsx                    # 教育背景（editable）
│   ├── InternshipCard.tsx                   # 实习段
│   ├── ProjectCard.tsx                      # 项目（支持 PullQuote）
│   ├── SkillChips.tsx                       # 按 level 分组 chip
│   ├── KnowledgeChips.tsx                   # 知识领域 chip
│   ├── SoftSkillRow.tsx                     # 一行软技能（维度 + 叙事 + tag）
│   ├── SjtCta.tsx                           # SJT 测评 CTA 大 card
│   ├── GoalCard.tsx                         # 当前目标展示
│   └── RecommendationCard.tsx               # 单个推荐（去审判版）
├── forms/
│   ├── EducationEdit.tsx                    # 内联编辑教育
│   ├── InternshipEdit.tsx                   # 内联编辑实习
│   ├── ProjectEdit.tsx                      # 内联编辑项目
│   └── SkillEdit.tsx                        # 加技能
├── UploadCta.tsx                            # 上传简历按钮（带 progress）
├── ManualProfileForm.tsx                    # 手动录入（迁移 v1，视觉重做）
└── mockData.ts                              # `?mock=1` 演示
```

---

## VI. 布局与响应式

**桌面**（≥1024px）：
- 内容最大宽度 `max-w-[1200px] mx-auto`
- 左右 padding `px-20`（略紧 Report）
- 双列：`lg:grid-cols-[1fr_200px]` 右侧 TOC sticky
- 章节之间 `py-16 md:py-24`（跟 Report 密度调整后一致）

**平板**：
- `max-w-[720px]`
- 左右 `px-12`
- TOC 隐藏

**移动**：
- 左右 `px-6`
- 章节 `py-12`
- Skill chip 换行显示

---

## VII. Motion（复用 Report 经验）

- Chapter entrance：framer-motion stagger fade-in（复用 Chapter 组件）
- ChapterOpener：useScroll + useTransform（opacity 0.3→0.6 / scale 0.95→1）
- PullQuote 进入视野：opacity + border width 动画
- DropCap 首字：color 从 ink-2 → chestnut 过渡
- **新增** 编辑态切换：inline edit 打开/关闭用 `grid-template-rows` 动画（非 height），240ms ease-out-quart
- **新增** 上传 progress：圆环动画（不是进度条 bar）
- 全部受 `prefers-reduced-motion` 控制

---

## VIII. 交互细节

### 首访 vs 复访的差异

| 状态 | Prologue | Chapter I-IV 展示 | 主 CTA |
|---|---|---|---|
| 首访（0 profile） | 大 hero + 温柔欢迎 | 全部显示"空状态"温柔引导 | `[上传简历]` `[手动讲]` 2 个大 CTA |
| 复访（有 profile） | 小 hero + "已认识 N 天" | 展示已填内容 + "补充/编辑"小按钮 | 顶部导航一个小"重新上传"链接 |

### 上传流程

- 点 `[上传简历]` 打开文件选择
- 上传中：圆环 progress + 文案 "{{step}}"（对应 `uploadStep`）
- 成功：自动刷新 profile + 如果 name 空则弹出名字补录弹窗
- 失败：温柔 error 卡片 + 重试按钮

### 编辑模式

- 每个 card 右上角有小 icon `<Pencil/>`，hover 显示
- 点击切 inline edit，保留布局（不跳 modal）
- 保存：乐观更新 + 后端同步
- 删除：先二次确认（`ConfirmDialog`）

### 空状态的语气

**砍掉**：
- "请填写教育背景"（命令）
- "必填"（评判）

**换成**：
- "先讲讲学校和专业吧" / "有也好，没有也行 —— 这些都可以晚点补" / "几个字就够了"

---

## IX. 验收标准

1. **首屏感受像"打开一份私人档案"**：owner 打开 `/profile?mock=1`，第一眼不是 dashboard 而是"一封档案开场信"
2. **无审判数字**：整页无百分比 / overall_score / 行业平均 / AI风险标签 / 安全区/风险区
3. **首访有明显上传入口**：`/profile` 清空 mock 后页首 2 个大 CTA 明显
4. **Editorial 装饰齐**：每章 Kicker + ChapterOpener；Chapter I / II 必有 DropCap；如果有用户原话则有 PullQuote
5. **TOC 侧栏工作**：lg+ 尺寸右侧 4 章目录，滚动时高亮当前章
6. **编辑内联**：点编辑不跳 modal，保留布局
7. **空状态语气温柔**：不出现"必填 / 请填写 / 需要"等命令/评判词
8. **真实数据也能跑**（不仅 mock）：未登录时跳登录，已登录时 `/profile/me` 返回数据能渲染
9. **tsc 0 错误 + curl 200**
10. **移动端可读**：iPhone 14 下每章一屏内可见关键 CTA

---

## X. 不做的事

- ❌ 不动 backend（API 全复用）
- ❌ 不做 profile 导出 / 分享 / PDF（后续）
- ❌ 不做 profile 版本历史（后续）
- ❌ 不做多 profile 切换（一个用户一份 profile）
- ❌ 不引入 WYSIWYG 编辑器（内联编辑只允许纯文本 + 基本 chip）
- ❌ 不做 Markdown 渲染（用户输入都是纯文本）
- ❌ 不做拖拽排序（Skills / Projects 顺序由后端决定）
- ❌ 不在 Profile 页做 CoachAgent 调用（Coach 有独立页）

---

## XI. 给 Kimi 的执行顺序

**前置**：`docs/v2-frontend-scaffold-spec.md` + `docs/v2-report-page-spec.md` 已完成（frontend-v2 + editorial 组件 + TableOfContents + ReportPage 都已落地）

1. **读后端** — 读 `backend/routers/profiles.py` + `backend/services/profile/` 了解 `/profiles/me` / `/profiles/{id}` endpoint 实际返回 shape
2. **拷贝 API client** — `frontend-v2/src/api/profiles.ts` 从 v1 拷贝 + 扩展 v2 所需方法（如 updateEducation / addInternship / 等）
3. **拷贝 hooks** — `useProfileData` / `useResumeUpload` 从 v1 迁移（如果有深度 v1 依赖则重写）
4. **实现 card 组件** — `src/components/profile-v2/cards/*` 9 个
5. **实现 forms 组件** — `src/components/profile-v2/forms/*` 4 个
6. **实现 UploadCta + ManualProfileForm** — 从 v1 `UploadProgress` + `ManualProfileForm` 迁移但视觉完全重做
7. **实现 6 个章节组件** — `ProfilePrologue + ProfileChapterI-IV + ProfileEpilogue`
8. **实现 ProfilePage.tsx** — 顶层 + loading/error/empty 态 + `?mock=1` 演示
9. **路由注册** — `src/App.tsx` `/profile` → ProfilePage
10. **TOC items 更新** — Profile TOC 4 条（I-IV）
11. **Motion 集成** — 按 §VII
12. **验证** — §IX 10 项逐项对
13. **截图** — 首访 / 复访 / 编辑态 / 上传中 4 张图 + 整页 1 张
14. **commit** — message：`feat(frontend-v2): profile page v2 (editorial editable archive)`

**必做验证**（吸取上轮教训）：
- `cd frontend-v2 && npx tsc --noEmit` → EXIT 0
- `npm run dev` 保持运行（5174 LISTEN）
- `curl http://localhost:5174/profile?mock=1` → HTTP 200
- `curl http://localhost:5174/profile` → HTTP 200（未登录跳登录是正常的，但 HTTP 本身要 200）

**完成后回**：`"ProfilePage v2 完成 + 5 张截图 + curl 200 + git xxxxxx"`

---

**完成判定**：owner 打开 `http://localhost:5174/profile?mock=1` 感到像 "打开一份私人档案"，**不是 dashboard / form**。编辑流程不跳 modal、不打分、不评判。
