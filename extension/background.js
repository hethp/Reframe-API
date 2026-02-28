// handle popup/chat/backend requests
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "PROCESS_NEWS") {
    fetch("http://localhost:8000/process-news", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ url: request.url })
    })
      .then(res => res.json())
      .then(data => sendResponse({ success: true, data: data }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    // Return true to indicate we will send a response asynchronously
    return true;
  }

  if (request.type === "CHAT") {
    fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ url: request.url, message: request.message, generation: request.generation })
    })
      .then(res => res.json())
      .then(data => sendResponse({ success: true, data: data }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    // Return true to indicate we will send a response asynchronously
    return true;
  }
});

// when the user clicks the toolbar icon, either open the side panel (if supported)
// or inject a floating sidebar into the current page
chrome.action.onClicked.addListener((tab) => {
  if (chrome.sidePanel && chrome.sidePanel.open) {
    // open the built-in side panel provided by newer Chrome/Edge
    chrome.sidePanel.open();
  } else {
    // fallback: inject a sidebar iframe into the page
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ['injectSidebar.js']
    });
  }
});

