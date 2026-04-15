# v2 LoginPage · 轻到几乎看不见的入口

> 创建：2026-04-15
> 状态：待 Kimi 实施
> 依赖：`.impeccable.md` v2.0 / `v2-frontend-scaffold-spec.md` / 复用 backend `/api/auth/*`
> Editorial Intensity 🌟（极简 — 入口克制 editorial）

---

## I. 用户 Job to be done

**用户**：第一次来的访客 / 已注册但被踢下线的老用户。

**场景**：
- 首次 — 在 HomePage 点"开始"被要求注册
- 老用户 — 访问 `/profile` 等需登录页面时被 redirect 过来

**核心诉求**：30 秒内完成（登录或注册），不要被这个页面分心。

**情绪**：
- 不要被"华丽动画"惊到（v1 的 depth cards parallax 是过度设计）
- 不要被蓝色按钮压迫（`#2563eb` gradient 是 AI slop 一号 tell）
- 不要觉得这是"严肃的企业软件"

---

## II. 顶层设计 · 一页纸登录

**Editorial Intensity 🌟** — 比其他页都克制。入口页不需要 DropCap / PullQuote 这些装饰。

**不做的** vs **要做的**

| 不做 | 要做 |
|---|---|
| ❌ Parallax depth cards | ✅ 纯静态布局 |
| ❌ Ambient glow blue radial | ✅ 统一 bg-paper + noise overlay（已有） |
| ❌ Gradient button `#2563eb→#1d4ed8` | ✅ Chestnut 实色 button |
| ❌ Logo 放在 blue gradient 底 | ✅ Logo 放在无装饰区，或用 Roman I·II 代替 |
| ❌ framer-motion 6-段 staggered fade | ✅ 单次 fade-in 300ms |
| ❌ "记住我" 蓝色 link | ✅ "记住我" 中性色 checkbox |

**品牌一致**：
- 字体：`--font-display` (Bricolage) for 标题，`--font-sans` (Geist) for body/form
- 色板：`--bg-paper` 底，`--ink-1/2/3` 文字，`--chestnut` 主 CTA，`--ember` 错误
- 图标：lucide icons，不要 emoji

---

## III. IA · 单页结构

```
┌──────────────────────────────────────┐
│                                      │
│                                      │ ← 上方留白 128-192px
│                                      │
│   EDITORIAL · 职途智析                 │ ← Kicker
│                                      │
│   登录                                 │ ← display-lg hero
│                                      │
│   一份只给你自己的档案。                │ ← body-lg intro
│                                      │
│   ─────────────────────              │ ← hairline
│                                      │
│   用户名                               │
│   [input                        ]    │
│                                      │
│   密码                                 │
│   [input                        ]    │
│                                      │
│   [ 登录 ]                             │ ← chestnut button
│                                      │
│   没有账号？ 立即注册 →                  │ ← tab 切换用小字链接
│                                      │
│                                      │
└──────────────────────────────────────┘
```

**登录 / 注册 Tab 切换**：
- 不用 v1 的 tab bar（bg-[#f5f5f5] rounded pill tab）— 太 SaaS
- 改用**文字链接切换**（像杂志里一句话）
- Hero title 根据 tab 切换 "登录" / "注册"

**Error 态**：错误信息在表单下方用 `--ember` 色一行软化文案显示（不用红色 bg 框）

**Success 态**：登录成功立即 navigate 到 `/`，不 flash 任何提示

---

## IV. 数据契约

**后端不动** — 复用现有 endpoints：

```
POST /api/auth/login    body: { username, password }
POST /api/auth/register body: { username, password }

Response:
{
  success: boolean,
  data: { token: string, user: { id, username, ... } },
  message?: string  // 错误时
}
```

**Token 存储**：
- `localStorage.setItem('token', data.data.token)`
- `localStorage.setItem('user', JSON.stringify(data.data.user))`
- 这两行 v1 已经在做，v2 保留逻辑

**已登录跳转**：
- `useAuth().isAuthenticated` 为 true 时自动 `navigate('/')`

---

## V. 组件拆分

```
src/pages/LoginPage.tsx    # 单文件，约 150-180 行（不拆 sub-component）
```

不新建 sub 组件。LoginPage 单文件解决：
- useAuth 检测
- form state（username/password/tab）
- submit handler
- render

---

## VI. 布局与响应式

**桌面**：
- 整页 min-h-screen
- 内容 `max-w-[420px] mx-auto` 居中
- 垂直居中：`flex items-center justify-center`
- 上下 padding：`py-20`

**平板**：同桌面

**移动**：
- `max-w-[420px]` 自然收缩
- `px-6` 左右边距

---

## VII. Motion

**极简**（不要 v1 那种 6 段 staggered）：

- 进入页面：整个卡片 fade-in + 上移 12px（一次，300ms ease-out-quart）
- submit 按钮 loading：只有文案变化 "登录中…"，不加 spinner（保持静）
- Tab 切换：hero title 用 `AnimatePresence` 做简单 fade-cross（200ms）
- 输入框 focus：`focus-visible` 态用 `--chestnut/30` 2px outline（不要 box-shadow glow）
- 全部受 `prefers-reduced-motion` 控制

---

## VIII. 组件实现骨架

```tsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '@/hooks/useAuth'

export default function LoginPage() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true })
  }, [isAuthenticated, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) {
      setError('用户名和密码都填一下')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/auth/${tab}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || '没通过 —— 再试一下')
        return
      }
      if (data.success && data.data?.token) {
        localStorage.setItem('token', data.data.token)
        localStorage.setItem('user', JSON.stringify(data.data.user))
        navigate('/')
      } else {
        setError(data.message || '没通过 —— 再试一下')
      }
    } catch {
      setError('连不上后端 —— 检查一下服务')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-[var(--bg-paper)] flex items-center justify-center px-6 py-20">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-[420px]"
      >
        {/* Kicker */}
        <p className="font-sans text-[13px] font-bold uppercase tracking-[0.22em] text-[var(--chestnut)] mb-5">
          Editorial · 职途智析
        </p>

        {/* Hero title */}
        <AnimatePresence mode="wait">
          <motion.h1
            key={tab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="font-display font-medium text-[var(--fs-display-lg)] leading-[var(--lh-display)] text-[var(--ink-1)] tracking-tight"
          >
            {tab === 'login' ? '登录' : '注册'}
          </motion.h1>
        </AnimatePresence>

        {/* Intro */}
        <p className="mt-3 font-sans text-[var(--fs-body-lg)] leading-[var(--lh-body-zh)] text-[var(--ink-2)]">
          一份只给你自己的档案。
        </p>

        {/* Hairline */}
        <div className="mt-10 mb-8 h-px bg-[var(--line)]" />

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block font-sans text-[var(--fs-body-sm)] text-[var(--ink-3)] mb-2">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              className="w-full px-4 py-3 bg-[var(--bg-card)] border border-[var(--line)] rounded-md text-[var(--fs-body)] text-[var(--ink-1)] outline-none focus:border-[var(--chestnut)]/60 focus:ring-2 focus:ring-[var(--chestnut)]/20 transition-colors"
            />
          </div>
          <div>
            <label className="block font-sans text-[var(--fs-body-sm)] text-[var(--ink-3)] mb-2">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              className="w-full px-4 py-3 bg-[var(--bg-card)] border border-[var(--line)] rounded-md text-[var(--fs-body)] text-[var(--ink-1)] outline-none focus:border-[var(--chestnut)]/60 focus:ring-2 focus:ring-[var(--chestnut)]/20 transition-colors"
            />
          </div>

          {error && (
            <p className="text-[var(--fs-body-sm)] text-[var(--ember)]">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-md bg-[var(--chestnut)] text-white text-[var(--fs-body)] font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {loading ? (tab === 'login' ? '登录中…' : '注册中…') : (tab === 'login' ? '登录' : '注册')}
          </button>
        </form>

        {/* Tab switch (text link) */}
        <p className="mt-8 text-[var(--fs-body-sm)] text-[var(--ink-3)]">
          {tab === 'login' ? '没有账号？' : '已有账号？'}
          <button
            type="button"
            onClick={() => {
              setTab(tab === 'login' ? 'register' : 'login')
              setError('')
            }}
            className="ml-2 text-[var(--ink-1)] underline underline-offset-4 hover:text-[var(--chestnut)] transition-colors"
          >
            {tab === 'login' ? '立即注册 →' : '立即登录 →'}
          </button>
        </p>
      </motion.div>
    </main>
  )
}
```

---

## IX. 验收标准

1. **整页极简感**：没有 parallax / gradient button / ambient glow / depth cards
2. **色板统一**：全部用 OKLCH 变量，零蓝色
3. **Tab 切换顺畅**：hero title fade-cross，200ms
4. **错误软化**：文案不是"操作失败"这种冷词，是"没通过 —— 再试一下"
5. **已登录跳转**：isAuthenticated 为 true 时立即 navigate `/`，无闪烁
6. **Form validation**：空字段 → 内联错误提示
7. **真实后端可用**：后端跑着时 POST /api/auth/login 成功，存 token，跳 `/`
8. **tsc EXIT 0** + **curl /login HTTP 200**
9. **移动端可用**：iPhone 14 视角下表单在一屏内

---

## X. 不做的事

- ❌ 不做 OAuth / Google / GitHub 登录
- ❌ 不做"忘记密码"跳转（v1 有 `#` 空链接，直接删）
- ❌ 不做"记住我" checkbox（token 默认 localStorage 持久化，不需要这个选项）
- ❌ 不做验证码 / 2FA
- ❌ 不做 decorative depth cards / parallax
- ❌ 不引入新依赖

---

## XI. 给 Kimi 的执行顺序

1. 新建 `frontend-v2/src/pages/LoginPage.tsx`（按 §VIII 骨架）
2. `src/App.tsx` 加路由 `<Route path="/login" element={<LoginPage />} />`
3. 检查 `useAuth` hook 是否已在 v2（应该有，v2 hooks 已从 v1 拷贝）
4. `cd frontend-v2 && npx tsc --noEmit` → EXIT 0
5. `curl http://localhost:5174/login` → HTTP 200
6. 浏览器访问 `/login` 验证视觉（奶米底 + 栗色按钮 + 无蓝色）
7. 截图 3 张：整页 / 错误态 / 注册 tab
8. **必做 commit**:
   ```
   git add frontend-v2/
   git commit -m "feat(frontend-v2): login page (minimal editorial)

   - 单文件实现，约 180 行
   - 登录/注册 tab 用文字链接切换（hero title fade-cross）
   - 砍 v1 parallax depth cards / ambient glow / gradient button
   - Chestnut 主 CTA，ember 错误文案
   - 错误文案软化 ('没通过 —— 再试一下')
   - 表单 autoComplete + focus ring chestnut/20

   Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
   ```

**完成判定**：owner 打开 `/login` 感到"轻到几乎看不见的入口"，30 秒完成登录，进入 `/` 后感觉无缝衔接 v2 整体设计。
