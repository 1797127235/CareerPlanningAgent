// Background service worker: relay JD from content script to local backend.

const DEFAULT_APP_URL = "http://localhost:5173"

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  // One-click binding: frontend posts token back via content script
  if (msg.type === "LINK_TOKEN") {
    chrome.storage.local.set({ extensionToken: msg.token }, () => {
      sendResponse({ success: true })
    })
    return true
  }

  // Popup requests to open the link page
  if (msg.type === "OPEN_LINK_PAGE") {
    chrome.storage.local.get(["appUrl"], (cfg) => {
      const appUrl = (cfg.appUrl || DEFAULT_APP_URL).replace(/\/$/, "")
      chrome.tabs.create({ url: `${appUrl}/jd?ext_link=1` })
    })
    return false
  }

  if (msg.type !== "SEND_JD") return false

  chrome.storage.local.get(["appUrl", "extensionToken"], async (cfg) => {
    const appUrl = (cfg.appUrl || DEFAULT_APP_URL).replace(/\/$/, "")
    const token = cfg.extensionToken || ""

    if (!token) {
      sendResponse({ success: false, error: "请先连接助手（点扩展图标→一键连接）" })
      return
    }

    let sessionId
    try {
      const resp = await fetch(`${appUrl}/api/extension/jd`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-extension-token": token,
        },
        body: JSON.stringify(msg.payload),
      })

      if (resp.status === 401) {
        sendResponse({ success: false, error: "令牌已过期，请重新连接" })
        return
      }
      if (!resp.ok) {
        sendResponse({ success: false, error: `服务器错误 (${resp.status})` })
        return
      }

      const data = await resp.json()
      sessionId = data.session_id
    } catch {
      sendResponse({ success: false, error: "无法连接到助手，请确认服务已启动" })
      return
    }

    // Respond first so the content script can show the success toast
    sendResponse({ success: true })

    // Save last sent timestamp
    chrome.storage.local.set({ last_sent: Date.now() })

    // Delay tab switch so user sees the success state on the job page
    await new Promise((r) => setTimeout(r, 1500))

    const jdUrl = `${appUrl}/jd?ext_session=${sessionId}`
    const tabs = await chrome.tabs.query({ url: `${appUrl}/*` })
    if (tabs.length > 0) {
      await chrome.tabs.update(tabs[0].id, { active: true, url: jdUrl })
      chrome.windows.update(tabs[0].windowId, { focused: true })
    } else {
      chrome.tabs.create({ url: jdUrl })
    }
  })

  return true // keep sendResponse channel open for async
})
