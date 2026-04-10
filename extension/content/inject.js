// Content script: detect platform, wait for JD DOM, inject send button.

const MIN_JD_LENGTH = 50

function detectPlatform() {
  const host = location.hostname.replace(/^www\./, "")
  return Object.keys(PLATFORMS).find((p) => host.includes(p)) || null
}

function queryFirst(selectors) {
  for (const sel of selectors) {
    try {
      const el = document.querySelector(sel)
      if (el && el.innerText.trim().length >= MIN_JD_LENGTH) return el
    } catch (_) { /* invalid selector — skip */ }
  }
  return null
}

function extractJD(platformKey) {
  const cfg = PLATFORMS[platformKey]
  const titleEl = document.querySelector(cfg.titleSelector)
  const bodyEl = queryFirst(cfg.bodySelectors)
  if (!bodyEl) return null
  return {
    page_title: titleEl?.innerText.trim() || document.title,
    jd_text: bodyEl.innerText.trim(),
    source_url: location.href,
  }
}

function setButtonState(btn, state, text) {
  btn.textContent = text
  btn.disabled = state === "loading" || state === "done"
  btn.dataset.state = state
}

function showToast(text, type = "success") {
  const existing = document.getElementById("cpa-toast")
  if (existing) existing.remove()

  const toast = document.createElement("div")
  toast.id = "cpa-toast"
  toast.textContent = text
  toast.dataset.type = type
  document.body.appendChild(toast)

  setTimeout(() => toast.remove(), 3000)
}

function injectButton(platformKey) {
  if (document.getElementById("cpa-jd-btn")) return

  const btn = document.createElement("button")
  btn.id = "cpa-jd-btn"
  btn.textContent = "发送到职业规划助手"

  btn.addEventListener("click", () => {
    const jd = extractJD(platformKey)
    if (!jd) {
      setButtonState(btn, "error", "❌ 请先登录后查看 JD")
      setTimeout(() => setButtonState(btn, "idle", "发送到职业规划助手"), 3000)
      return
    }

    setButtonState(btn, "loading", "发送中…")
    chrome.runtime.sendMessage({ type: "SEND_JD", payload: jd }, (res) => {
      if (chrome.runtime.lastError || !res?.success) {
        const msg = res?.error || chrome.runtime.lastError?.message || "发送失败"
        setButtonState(btn, "error", `❌ ${msg}`)
        showToast(`❌ ${msg}`, "error")
        setTimeout(() => setButtonState(btn, "idle", "发送到职业规划助手"), 4000)
      } else {
        setButtonState(btn, "done", "✅ 已发送，正在打开助手…")
        showToast("✅ JD 已发送，即将跳转到助手")
        // Button resets after tab switch completes (2s)
        setTimeout(() => setButtonState(btn, "idle", "发送到职业规划助手"), 2500)
      }
    })
  })

  document.body.appendChild(btn)
}

function init() {
  const platformKey = detectPlatform()
  if (!platformKey) return

  const cfg = PLATFORMS[platformKey]

  // Try immediately for static pages
  if (queryFirst(cfg.bodySelectors)) {
    injectButton(platformKey)
    return
  }

  // SPA: observe DOM until JD content appears, with 10s timeout
  const timer = setTimeout(() => observer.disconnect(), 10_000)
  const observer = new MutationObserver(() => {
    if (queryFirst(cfg.bodySelectors)) {
      clearTimeout(timer)
      observer.disconnect()
      injectButton(platformKey)
    }
  })
  observer.observe(document.body, { childList: true, subtree: true })
}

init()
