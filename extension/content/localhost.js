// Bridge between the assistant frontend and the extension background.
// Runs on http://localhost:5173/* as a content script.

// Tell the page the extension is installed
window.postMessage({ type: "CPA_EXT_READY" }, "*")

// Relay token link-back from the page to background
window.addEventListener("message", (evt) => {
  if (evt.source !== window) return
  if (evt.data?.type === "CPA_LINK_TOKEN") {
    chrome.runtime.sendMessage({ type: "LINK_TOKEN", token: evt.data.token }, () => {
      window.postMessage({ type: "CPA_LINK_TOKEN_ACK" }, "*")
    })
  }
})
