const DEFAULT_APP_URL = "http://localhost:5173"

function formatLastSent(ts) {
  if (!ts) return ""
  const diff = Math.floor((Date.now() - ts) / 1000)
  if (diff < 60) return `上次发送：刚刚`
  if (diff < 3600) return `上次发送：${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `上次发送：${Math.floor(diff / 3600)} 小时前`
  return `上次发送：${Math.floor(diff / 86400)} 天前`
}

function renderStatus(cfg) {
  const connected = !!cfg.extensionToken
  const dot = document.getElementById("statusDot")
  const text = document.getElementById("statusText")
  const sub = document.getElementById("statusSub")
  const connectBtn = document.getElementById("connectBtn")
  const openBtn = document.getElementById("openBtn")

  if (connected) {
    dot.className = "dot connected"
    text.textContent = "已连接"
    sub.textContent = formatLastSent(cfg.last_sent)
    connectBtn.textContent = "重新连接"
    connectBtn.style.display = "block"
    openBtn.style.display = "block"
  } else {
    dot.className = "dot disconnected"
    text.textContent = "未连接"
    sub.textContent = "点击下方按钮完成连接"
    connectBtn.textContent = "一键连接助手"
    connectBtn.style.display = "block"
    openBtn.style.display = "none"
  }

  // Pre-fill manual config fields
  document.getElementById("appUrl").value = cfg.appUrl || DEFAULT_APP_URL
  document.getElementById("token").value = cfg.extensionToken || ""
}

// Load state on open
chrome.storage.local.get(["appUrl", "extensionToken", "last_sent"], renderStatus)

// One-click connect: open the link page
document.getElementById("connectBtn").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "OPEN_LINK_PAGE" })
  window.close()
})

// Open assistant home
document.getElementById("openBtn").addEventListener("click", () => {
  chrome.storage.local.get(["appUrl"], (cfg) => {
    const appUrl = (cfg.appUrl || DEFAULT_APP_URL).replace(/\/$/, "")
    chrome.tabs.create({ url: `${appUrl}/jd` })
    window.close()
  })
})

// Advanced toggle
document.getElementById("advancedToggle").addEventListener("click", () => {
  const body = document.getElementById("advancedBody")
  const arrow = document.getElementById("advancedArrow")
  const open = body.classList.toggle("open")
  arrow.textContent = open ? "▴" : "▾"
})

// Manual save
document.getElementById("saveBtn").addEventListener("click", () => {
  const appUrl = document.getElementById("appUrl").value.trim().replace(/\/$/, "")
  const extensionToken = document.getElementById("token").value.trim()
  chrome.storage.local.set({ appUrl, extensionToken }, () => {
    const s = document.getElementById("saveStatus")
    s.textContent = "✓ 已保存"
    setTimeout(() => {
      s.textContent = ""
      renderStatus({ appUrl, extensionToken })
    }, 1500)
  })
})
