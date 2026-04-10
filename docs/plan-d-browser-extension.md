# Plan D — 浏览器扩展「JD 一键导入」技术方案

## 目标

用户在 BOSS直聘、拉勾、猎聘等登录墙招聘网站上查看 JD 时，点一个按钮即可将 JD 发送到职业规划助手，无需手动复制粘贴。

---

## 整体架构

```
招聘网站页面（用户已登录）
    │  content script 读取 DOM
    ▼
扩展 Content Script (inject.js)
    │  chrome.runtime.sendMessage
    ▼
扩展 Background Worker (background.js)
    │  fetch POST /api/jd/from-extension
    ▼
本地后端 (FastAPI)
    │  存入 pending_jd 临时表 / Redis
    ▼
前端 JD 页面（SSE 或轮询）
    │  自动填入 JD 文本
    ▼
用户点击「开始诊断」
```

---

## 文件结构

```
extension/
├── manifest.json
├── background.js
├── popup/
│   ├── popup.html
│   └── popup.js
├── content/
│   ├── inject.js          # 通用入口：识别平台 + 注入按钮
│   ├── platforms.js       # 各平台 DOM 选择器配置
│   └── inject.css         # 悬浮按钮样式
└── icons/
    ├── icon16.png
    └── icon48.png
```

---

## manifest.json（Manifest V3）

```json
{
  "manifest_version": 3,
  "name": "职业规划助手 - JD 一键导入",
  "version": "1.0.0",
  "description": "在招聘网站上一键将 JD 发送到职业规划助手",
  "permissions": ["activeTab", "storage", "scripting", "tabs", "notifications"],
  "host_permissions": [
    "https://www.zhipin.com/*",
    "https://www.lagou.com/*",
    "https://www.liepin.com/*",
    "https://sou.zhaopin.com/*",
    "https://www.zhaopin.com/*",
    "https://we.51job.com/*",
    "https://search.51job.com/*"
  ],
  "content_scripts": [
    {
      "matches": [
        "https://www.zhipin.com/job_detail/*",
        "https://m.zhipin.com/jobs/*",
        "https://www.lagou.com/jobs/*",
        "https://www.lagou.com/wn/jobs/*",
        "https://www.liepin.com/job/*",
        "https://www.zhaopin.com/jobs/*",
        "https://we.51job.com/*"
      ],
      "js": ["content/inject.js"],
      "css": ["content/inject.css"],
      "run_at": "document_idle"
    }
  ],
  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png"
    }
  },
  "background": {
    "service_worker": "background.js"
  }
}
```

---

## platforms.js — 各平台 DOM 选择器

```js
// content/platforms.js
const PLATFORMS = {
  "zhipin.com": {
    name: "BOSS直聘",
    titleSelector: ".job-detail-header .name",
    bodySelectors: [
      ".job-detail-section .text",
      ".job-sec-text",
      "[class*='detail-content']"
    ]
  },
  "lagou.com": {
    name: "拉勾",
    titleSelector: ".position-name, .job-name",
    bodySelectors: [
      ".job-detail",
      ".job_describe",
      "[class*='describe']"
    ]
  },
  "liepin.com": {
    name: "猎聘",
    titleSelector: ".title-info h1, .job-name",
    bodySelectors: [
      ".job-introduction",
      ".job-description",
      "[class*='description']"
    ]
  },
  "zhaopin.com": {
    name: "智联招聘",
    titleSelector: ".name__title, h1",
    bodySelectors: [
      ".describtion",
      ".job-detail",
      "[class*='detail']"
    ]
  },
  "51job.com": {
    name: "前程无忧",
    titleSelector: ".cn h1, .job-name",
    bodySelectors: [
      ".bmsg",
      ".job-detail",
      "[class*='detail']"
    ]
  }
}
```

---

## inject.js — Content Script 核心

```js
// content/inject.js

// 识别当前平台
function detectPlatform() {
  const host = location.hostname.replace("www.", "")
  return Object.keys(PLATFORMS).find(p => host.includes(p))
}

// 尝试多个选择器，返回第一个有内容的
function queryFirst(selectors) {
  for (const sel of selectors) {
    const el = document.querySelector(sel)
    if (el && el.innerText.trim().length > 50) return el
  }
  return null
}

// 提取 JD 文本
function extractJD(platform) {
  const config = PLATFORMS[platform]
  const titleEl = document.querySelector(config.titleSelector)
  const bodyEl = queryFirst(config.bodySelectors)

  if (!bodyEl) return null

  const title = titleEl?.innerText.trim() || document.title
  const body = bodyEl.innerText.trim()
  return { title, body, url: location.href }
}

// 注入悬浮按钮
function injectButton(platform) {
  if (document.getElementById("cpa-jd-btn")) return

  const btn = document.createElement("button")
  btn.id = "cpa-jd-btn"
  btn.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
    发送到职业规划助手
  `
  btn.onclick = async () => {
    const jd = extractJD(platform)
    if (!jd) {
      btn.textContent = "❌ 未找到 JD 内容"
      return
    }
    btn.textContent = "发送中..."
    btn.disabled = true
    chrome.runtime.sendMessage({ type: "SEND_JD", payload: jd }, (res) => {
      if (res?.success) {
        btn.innerHTML = "✅ 已发送，请切换到助手"
      } else {
        btn.innerHTML = `❌ ${res?.error || "发送失败"}`
        btn.disabled = false
      }
    })
  }

  document.body.appendChild(btn)
}

// 主逻辑：等待页面完全渲染
function init() {
  const platform = detectPlatform()
  if (!platform) return

  // 部分平台是 SPA，需等待内容注入
  const observer = new MutationObserver(() => {
    const config = PLATFORMS[platform]
    const body = queryFirst(config.bodySelectors)
    if (body) {
      injectButton(platform)
      observer.disconnect()
    }
  })
  observer.observe(document.body, { childList: true, subtree: true })

  // 同时立即尝试（静态页面）
  injectButton(platform)
}

init()
```

---

## inject.css — 悬浮按钮样式

```css
#cpa-jd-btn {
  position: fixed;
  bottom: 32px;
  right: 32px;
  z-index: 99999;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: #2563eb;
  color: white;
  font-size: 14px;
  font-weight: 600;
  border: none;
  border-radius: 999px;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.4);
  cursor: pointer;
  transition: all 0.2s;
  font-family: -apple-system, sans-serif;
}
#cpa-jd-btn:hover {
  background: #1d4ed8;
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.5);
}
#cpa-jd-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}
```

---

## background.js — API 通信

```js
// background.js

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type !== "SEND_JD") return

  chrome.storage.local.get(["appUrl", "extensionToken"], async (cfg) => {
    const appUrl = cfg.appUrl || "http://localhost:5173"
    const token = cfg.extensionToken || ""

    if (!token) {
      sendResponse({ success: false, error: "请先在扩展设置中配置令牌" })
      return
    }

    try {
      const resp = await fetch(`${appUrl}/api/jd/from-extension`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Extension-Token": token
        },
        body: JSON.stringify({
          jd_text: msg.payload.body,
          page_title: msg.payload.title,
          source_url: msg.payload.url
        })
      })

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

      const data = await resp.json()

      // 打开/聚焦 web app 的 JD 页面
      const jdPageUrl = `${appUrl}/jd?ext_session=${data.session_id}`
      const tabs = await chrome.tabs.query({ url: `${appUrl}/*` })
      if (tabs.length > 0) {
        chrome.tabs.update(tabs[0].id, { active: true, url: jdPageUrl })
        chrome.windows.update(tabs[0].windowId, { focused: true })
      } else {
        chrome.tabs.create({ url: jdPageUrl })
      }

      sendResponse({ success: true })
    } catch (e) {
      sendResponse({ success: false, error: e.message })
    }
  })

  return true // 保持 sendResponse 通道异步有效
})
```

---

## popup/popup.html — 扩展设置弹窗

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body { width: 280px; padding: 16px; font-family: -apple-system, sans-serif; font-size: 13px; }
    h3 { margin: 0 0 12px; font-size: 15px; color: #1e293b; }
    label { display: block; color: #64748b; font-weight: 600; margin-bottom: 4px; }
    input {
      width: 100%; box-sizing: border-box;
      border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 8px 10px; font-size: 12px; margin-bottom: 10px;
    }
    button {
      width: 100%; padding: 9px; background: #2563eb; color: white;
      border: none; border-radius: 8px; font-weight: 600; cursor: pointer;
    }
    .status { font-size: 11px; color: #10b981; margin-top: 8px; text-align: center; }
  </style>
</head>
<body>
  <h3>⚡ 职业规划助手</h3>
  <label>助手地址</label>
  <input id="appUrl" placeholder="http://localhost:5173" />
  <label>扩展令牌</label>
  <input id="token" type="password" placeholder="从助手设置页获取" />
  <button id="save">保存设置</button>
  <div class="status" id="status"></div>
  <script src="popup.js"></script>
</body>
</html>
```

```js
// popup/popup.js
chrome.storage.local.get(["appUrl", "extensionToken"], (cfg) => {
  document.getElementById("appUrl").value = cfg.appUrl || "http://localhost:5173"
  document.getElementById("token").value = cfg.extensionToken || ""
})

document.getElementById("save").onclick = () => {
  const appUrl = document.getElementById("appUrl").value.trim().replace(/\/$/, "")
  const extensionToken = document.getElementById("token").value.trim()
  chrome.storage.local.set({ appUrl, extensionToken }, () => {
    document.getElementById("status").textContent = "✓ 已保存"
    setTimeout(() => { document.getElementById("status").textContent = "" }, 2000)
  })
}
```

---

## 后端需新增

### 1. 数据库表（或内存 dict）

```python
# 简单实现：module-level dict，TTL 10 分钟
import time, uuid
_PENDING_JDS: dict[str, dict] = {}  # session_id -> {jd_text, created_at}

def store_pending_jd(jd_text: str, source_url: str) -> str:
    sid = str(uuid.uuid4())
    _PENDING_JDS[sid] = {"jd_text": jd_text, "source_url": source_url, "ts": time.time()}
    return sid

def pop_pending_jd(sid: str) -> dict | None:
    entry = _PENDING_JDS.pop(sid, None)
    if entry and time.time() - entry["ts"] < 600:  # 10min TTL
        return entry
    return None
```

### 2. 扩展令牌表

```sql
CREATE TABLE extension_tokens (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
```

### 3. 新增两个路由（加入 `backend/routers/jd.py`）

```python
@router.post("/from-extension")
def receive_from_extension(
    req: ExtensionJDRequest,
    x_extension_token: str = Header(...),
    db: Session = Depends(get_db),
):
    """Accept JD submitted from the browser extension."""
    token_row = db.query(ExtensionToken).filter(
        ExtensionToken.token == x_extension_token,
        ExtensionToken.expires_at > datetime.utcnow()
    ).first()
    if not token_row:
        raise HTTPException(401, "令牌无效或已过期")
    
    session_id = store_pending_jd(req.jd_text, req.source_url)
    return {"session_id": session_id}


@router.get("/pending/{session_id}")
def get_pending_jd(session_id: str, user: User = Depends(get_current_user)):
    """Frontend polls this to retrieve JD sent from extension."""
    entry = pop_pending_jd(session_id)
    if not entry:
        raise HTTPException(404, "会话不存在或已过期")
    return entry
```

### 4. 前端 JdPage 监听 ext_session 参数

```tsx
// 在 JdPage.tsx 的 useEffect 中：
const extSession = searchParams.get('ext_session')
useEffect(() => {
  if (!extSession) return
  fetch(`/api/jd/pending/${extSession}`)
    .then(r => r.json())
    .then(data => {
      if (data.jd_text) setJdText(data.jd_text)
    })
    .catch(() => {})
}, [extSession])
```

---

## 本地开发流程

1. 在 `extension/` 目录下创建所有文件
2. 打开 `chrome://extensions`，开启「开发者模式」
3. 点「加载已解压的扩展程序」，选择 `extension/` 目录
4. 打开扩展 popup，填入 `http://localhost:5173` 和令牌
5. 访问 `zhipin.com` 任意 JD 页面，右下角出现蓝色按钮即成功
6. 修改代码后点扩展管理页的「刷新」按钮即可热更新

## 打包发布（可选）

```bash
cd extension
zip -r career-planner-extension.zip . -x "*.DS_Store"
```

上传到 Chrome Web Store Developer Dashboard 走审核流程（约 1-3 工作日）。

---

## 开发优先级

| 任务 | 估时 | 依赖 |
|------|------|------|
| `manifest.json` + 图标 | 30min | 无 |
| `inject.js` (BOSS直聘适配) | 1h | manifest |
| `inject.css` 悬浮按钮 | 30min | 无 |
| `background.js` API 通信 | 1h | 后端接口 |
| `popup.html/js` 设置页 | 30min | 无 |
| 后端令牌生成 + pending JD 接口 | 1.5h | 无 |
| 前端 JdPage 监听 ext_session | 30min | 后端 |
| 拉勾 / 猎聘 / 智联 / 51job 适配 | 2h | inject.js 骨架 |

**建议顺序**：先跑通 BOSS直聘 → 后端接口 → 前端接收 → 再扩展其他平台
