# Kimi 执行：首页增加"对话建档"入口

## 任务

在首页的 hero 区域，给无画像用户增加一个"对话建档"按钮，和"上传简历"同级。
点击后打开教练面板并自动发送建档触发消息。

只改 1 个文件：`frontend/src/pages/HomePage.tsx`

---

## 具体改动

### 位置

找到首页的 CTA 按钮区域（约第 139-160 行），当前有两个按钮：

```tsx
<label ...>
  <Upload /> 上传简历
</label>
<button onClick={() => navigate('/profile')}>
  <PenLine /> 手动填写
</button>
```

### 改动 1：引入 sendToCoach

在文件顶部 import 区域加：

```typescript
import { sendToCoach } from '@/hooks/useCoachTrigger'
```

再引入 MessageSquare 图标（在已有的 lucide-react import 行加）：

```typescript
import { ArrowRight, Upload, PenLine, MapPin, Target, User, Flame, BookOpen, FileSearch, Zap, MessageSquare } from 'lucide-react'
```

### 改动 2：CTA 区域改为三个按钮

把现有的两个按钮区域改成三个：

```tsx
<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ delay: 0.58, duration: 0.35, ease }}
  className="flex items-center gap-4"
>
  {/* 主 CTA：上传简历 */}
  <label
    htmlFor="home-file-input"
    className="flex items-center gap-2 px-7 py-3.5 rounded-xl bg-[var(--blue)] text-white text-[15px] font-semibold hover:brightness-110 transition-all cursor-pointer shadow-lg shadow-blue-500/25"
  >
    <Upload className="w-4 h-4" />
    上传简历
  </label>
  {/* 次 CTA：对话建档 */}
  <button
    onClick={() => sendToCoach('我没有简历，想通过对话建立画像')}
    className="flex items-center gap-2 px-5 py-3.5 rounded-xl border border-[var(--blue)]/30 text-[var(--blue)] text-[14px] font-semibold hover:bg-[var(--blue)]/[0.06] transition-all cursor-pointer"
  >
    <MessageSquare className="w-4 h-4" />
    对话建档
  </button>
  {/* 三级入口：手动填写 */}
  <button
    onClick={() => navigate('/profile')}
    className="flex items-center gap-2 px-4 py-3.5 text-slate-500 text-[14px] font-medium hover:text-slate-800 transition-colors cursor-pointer"
  >
    <PenLine className="w-4 h-4" />
    手动填写
  </button>
</motion.div>
```

### 改动 3：副标题文案微调

把副标题（约第 135 行）从：

```
上传简历，告诉我你是谁——
我来帮你找方向、准备面试、分析差距。
```

改为：

```
上传简历或和教练聊聊，告诉我你是谁——
我来帮你找方向、准备面试、分析差距。
```

---

## sendToCoach 工作原理

`sendToCoach` 函数（来自 `useCoachTrigger.ts`）通过 `window.dispatchEvent` 派发一个 `coach-send` 自定义事件。
教练面板的 `useCoachTriggerListener` 会监听这个事件并自动发送消息。
教练面板如果已经打开，消息会直接发送；如果关闭了，事件仍会被缓存等面板打开时处理。

---

## 验收

1. 无画像用户首页看到三个按钮：`上传简历` | `对话建档` | `手动填写`
2. 点击"对话建档" → 教练面板收到消息"我没有简历，想通过对话建立画像"
3. 教练开始引导建档流程（前提：coach-profile-builder skill 已部署）
4. "上传简历"和"手动填写"功能不受影响
5. TypeScript 编译无错误

## 不要做

- 不改 Layout.tsx
- 不改 ChatPanel.tsx
- 不改后端
- 不加新依赖
